import threading
import time

from .runtime import Coroutine, GatherAwaitable, SleepAwaitable, Task, type_name


class Scheduler:
    def __init__(self, interpreter):
        self.interp = interpreter
        self.tasks = []
        self.current = None
        self.baton = threading.Event()
        try:
            threading.stack_size(64 * 1024 * 1024)
        except (ValueError, RuntimeError):
            pass

    def spawn(self, coro):
        if coro.task is not None:
            return coro.task
        task = Task("coro", coro)
        coro.task = task
        self.tasks.append(task)
        return task

    def as_task(self, awaitable, node):
        if isinstance(awaitable, Coroutine):
            return self.spawn(awaitable)
        if isinstance(awaitable, Task):
            return awaitable
        if isinstance(awaitable, SleepAwaitable):
            task = Task("sleep")
            task.wake = time.monotonic() + awaitable.seconds
            self.tasks.append(task)
            return task
        if isinstance(awaitable, GatherAwaitable):
            task = Task("gather")
            task.children = [self.as_task(item, node) for item in awaitable.items]
            self.tasks.append(task)
            return task
        raise self.interp.error(node, f"valores do tipo {type_name(awaitable)} não são aguardáveis")

    def await_(self, awaitable, node):
        task = self.as_task(awaitable, node)
        if self.current is None:
            self.drive(task)
        else:
            me = self.current
            while not task.done:
                me.waiting_on = task
                self.yield_current()
            me.waiting_on = None
        if task.error is not None:
            raise task.error
        return task.result

    def yield_current(self):
        me = self.current
        me.depth = self.interp.depth
        me.filename = self.interp.filename
        self.baton.set()
        me.event.wait()
        me.event.clear()

    def poll(self):
        now = time.monotonic()
        for task in self.tasks:
            if task.done:
                continue
            if task.kind == "sleep" and now >= task.wake:
                task.done = True
            elif task.kind == "gather":
                failed = next((c for c in task.children if c.done and c.error is not None), None)
                if failed is not None:
                    task.error = failed.error
                    task.done = True
                elif all(c.done for c in task.children):
                    task.result = [c.result for c in task.children]
                    task.done = True

    def is_ready(self, task):
        if task.done or task.kind != "coro":
            return False
        if not task.started:
            return True
        return task.waiting_on is not None and task.waiting_on.done

    def step(self, task):
        saved_depth = self.interp.depth
        saved_file = self.interp.filename
        self.current = task
        self.interp.depth = task.depth
        if task.filename:
            self.interp.filename = task.filename
        self.baton.clear()
        if not task.started:
            task.started = True
            task.thread = threading.Thread(target=self.run_task, args=(task,), daemon=True)
            task.thread.start()
        else:
            task.event.set()
        self.baton.wait()
        self.interp.depth = saved_depth
        self.interp.filename = saved_file
        self.current = None

    def run_task(self, task):
        coro = task.coro
        try:
            task.result = self.interp.invoke(coro.fn, coro.args, coro.kwargs, coro.node)
        except BaseException as error:
            task.error = error
        finally:
            task.done = True
            self.baton.set()

    def drive(self, target):
        while not target.done:
            self.tasks = [t for t in self.tasks if not t.done or t is target]
            self.poll()
            if target.done:
                break
            ready = [t for t in self.tasks if self.is_ready(t)]
            if ready:
                for task in ready:
                    if self.is_ready(task):
                        self.step(task)
                continue
            wakes = [t.wake for t in self.tasks if not t.done and t.kind == "sleep"]
            if not wakes:
                raise self.interp.error(None, "impasse: nenhuma tarefa pode continuar")
            time.sleep(max(0.0, min(wakes) - time.monotonic()))
