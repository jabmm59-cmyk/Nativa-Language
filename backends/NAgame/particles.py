"""
NAgame Particles Backend - Sistema de partículas
"""

import pygame
import math
import random


class Particula:
    """Partícula individual."""

    def __init__(self, x, y, vx=0, vy=0, vida=1.0, cor=(255, 255, 255),
                 tamanho=4, gravidade=0, fade=True, encolher=True):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.vida_max = float(vida)
        self.vida = float(vida)
        self.cor_base = cor
        self.cor = list(cor)
        self.tamanho_base = float(tamanho)
        self.tamanho = float(tamanho)
        self.gravidade = float(gravidade)
        self.fade = fade
        self.encolher = encolher
        self._viva = True

    @property
    def viva(self):
        return self._viva and self.vida > 0

    @property
    def progresso(self):
        return 1.0 - (self.vida / self.vida_max) if self.vida_max > 0 else 1.0

    def atualizar(self, dt):
        if not self._viva:
            return

        self.x += self.vx * dt
        self.vy += self.gravidade * dt
        self.y += self.vy * dt

        self.vida -= dt

        if self.vida <= 0:
            self._viva = False
            return

        prog = self.progresso

        if self.fade:
            alpha = int(255 * (1 - prog))
            self.cor[3] = alpha if len(self.cor) > 3 else alpha

        if self.encolher:
            self.tamanho = self.tamanho_base * (1 - prog)

    def desenhar(self, tela):
        if not self._viva:
            return

        tam = max(1, int(self.tamanho))
        cor = tuple(int(c) for c in self.cor[:3])
        alpha = self.cor[3] if len(self.cor) > 3 else 255

        if tam <= 2:
            # Desenhar como pixel/ponto para partículas pequenas
            pygame.draw.circle(tela, cor, (int(self.x), int(self.y)), tam)
        else:
            # Criar surface com alpha para partículas maiores
            surf = pygame.Surface((tam * 2, tam * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*cor, alpha), (tam, tam), tam)
            tela.blit(surf, (int(self.x - tam), int(self.y - tam)))


class EmissorParticulas:
    """Emissor de partículas."""

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.particulas = []
        self._ativo = True
        self._tempo_acumulado = 0.0

        # Configurações de emissão
        self.taxa = 10  # partículas por segundo
        self.rajada = 0  # partículas de uma vez (0 = contínuo)
        self.rajada_intervalo = 0
        self._ultima_rajada = 0

        # Propriedades das partículas
        self.vida_min = 0.5
        self.vida_max = 2.0
        self.velocidade_min = 50
        self.velocidade_max = 150
        self.angulo_min = 0
        self.angulo_max = 360
        self.gravidade = 0
        self.tamanho_min = 2
        self.tamanho_max = 6
        self.cores = [(255, 255, 255)]
        self.fade = True
        self.encolher = True

        # Forma de emissão
        self.forma = "ponto"  # "ponto", "circulo", "retangulo", "linha"
        self.raio_emissao = 0
        self.largura_emissao = 0
        self.altura_emissao = 0

    def emitir(self, quantidade=1):
        """Emite partículas manualmente."""
        for _ in range(quantidade):
            self._criar_particula()

    def _criar_particula(self):
        # Posição
        if self.forma == "circulo":
            ang = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, self.raio_emissao)
            px = self.x + math.cos(ang) * r
            py = self.y + math.sin(ang) * r
        elif self.forma == "retangulo":
            px = self.x + random.uniform(-self.largura_emissao/2, self.largura_emissao/2)
            py = self.y + random.uniform(-self.altura_emissao/2, self.altura_emissao/2)
        elif self.forma == "linha":
            t = random.random()
            px = self.x + t * self.largura_emissao
            py = self.y
        else:  # ponto
            px, py = self.x, self.y

        # Velocidade
        ang = math.radians(random.uniform(self.angulo_min, self.angulo_max))
        vel = random.uniform(self.velocidade_min, self.velocidade_max)
        vx = math.cos(ang) * vel
        vy = math.sin(ang) * vel

        # Vida
        vida = random.uniform(self.vida_min, self.vida_max)

        # Cor
        cor = random.choice(self.cores)
        if len(cor) == 3:
            cor = (*cor, 255)

        # Tamanho
        tamanho = random.uniform(self.tamanho_min, self.tamanho_max)

        particula = Particula(px, py, vx, vy, vida, cor, tamanho,
                              self.gravidade, self.fade, self.encolher)
        self.particulas.append(particula)

    def atualizar(self, dt):
        if self._ativo:
            self._tempo_acumulado += dt

            # Emissão contínua
            if self.taxa > 0 and self.rajada == 0:
                num = int(self._tempo_acumulado * self.taxa)
                if num > 0:
                    self.emitir(num)
                    self._tempo_acumulado -= num / self.taxa

            # Rajadas
            if self.rajada > 0 and self.rajada_intervalo > 0:
                if self._tempo_acumulado - self._ultima_rajada >= self.rajada_intervalo:
                    self.emitir(self.rajada)
                    self._ultima_rajada = self._tempo_acumulado

        # Atualizar partículas
        self.particulas = [p for p in self.particulas if p.viva]
        for p in self.particulas:
            p.atualizar(dt)

    def desenhar(self, tela):
        for p in self.particulas:
            p.desenhar(tela)

    def iniciar(self):
        self._ativo = True

    def parar(self):
        self._ativo = False

    def definir_posicao(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def limpar(self):
        self.particulas.clear()


class NAgameParticles:
    """Gerenciador de sistemas de partículas."""

    def __init__(self):
        self.emissores = []

    def criar_emissor(self, x, y, **kwargs):
        emissor = EmissorParticulas(x, y)
        for k, v in kwargs.items():
            if hasattr(emissor, k):
                setattr(emissor, k, v)
        self.emissores.append(emissor)
        return emissor

    # Presets comuns
    def criar_fogo(self, x, y):
        return self.criar_emissor(x, y,
            taxa=50, vida_min=0.2, vida_max=0.8,
            velocidade_min=20, velocidade_max=80,
            angulo_min=70, angulo_max=110,
            gravidade=-50,
            tamanho_min=4, tamanho_max=10,
            cores=[(255, 100, 0), (255, 200, 0), (255, 255, 0)],
            forma="retangulo", largura_emissao=20, altura_emissao=5
        )

    def criar_fumaca(self, x, y):
        return self.criar_emissor(x, y,
            taxa=15, vida_min=1.0, vida_max=3.0,
            velocidade_min=10, velocidade_max=30,
            angulo_min=60, angulo_max=120,
            gravidade=-20,
            tamanho_min=8, tamanho_max=20,
            cores=[(100, 100, 100), (150, 150, 150), (80, 80, 80)],
            fade=True, encolher=False
        )

    def criar_explosao(self, x, y, cor=(255, 100, 0)):
        emissor = self.criar_emissor(x, y,
            rajada=30, rajada_intervalo=0,
            vida_min=0.3, vida_max=1.0,
            velocidade_min=50, velocidade_max=200,
            angulo_min=0, angulo_max=360,
            gravidade=0,
            tamanho_min=3, tamanho_max=8,
            cores=[cor, (255, 255, 100), (255, 200, 0)],
            forma="circulo", raio_emissao=5
        )
        emissor.iniciar()
        return emissor

    def criar_estrelas(self, x, y):
        return self.criar_emissor(x, y,
            taxa=20, vida_min=0.5, vida_max=2.0,
            velocidade_min=5, velocidade_max=20,
            angulo_min=0, angulo_max=360,
            gravidade=0,
            tamanho_min=1, tamanho_max=3,
            cores=[(255, 255, 255), (200, 200, 255), (255, 255, 200)],
            fade=True
        )

    def atualizar(self, dt):
        for emissor in self.emissores[:]:
            emissor.atualizar(dt)
            # Remover emissores inativos sem partículas
            if not emissor._ativo and not emissor.particulas:
                self.emissores.remove(emissor)

    def desenhar(self, tela):
        for emissor in self.emissores:
            emissor.desenhar(tela)

    def limpar(self):
        self.emissores.clear()