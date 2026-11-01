"""
NAgame Physics Backend - Sistema de física 2D simples
"""

import math


class Vetor2D:
    """Vetor 2D para física."""

    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, outro):
        return Vetor2D(self.x + outro.x, self.y + outro.y)

    def __sub__(self, outro):
        return Vetor2D(self.x - outro.x, self.y - outro.y)

    def __mul__(self, escalar):
        return Vetor2D(self.x * escalar, self.y * escalar)

    def __truediv__(self, escalar):
        return Vetor2D(self.x / escalar, self.y / escalar)

    def __iadd__(self, outro):
        self.x += outro.x
        self.y += outro.y
        return self

    def __isub__(self, outro):
        self.x -= outro.x
        self.y -= outro.y
        return self

    def __imul__(self, escalar):
        self.x *= escalar
        self.y *= escalar
        return self

    def __itruediv__(self, escalar):
        self.x /= escalar
        self.y /= escalar
        return self

    def magnitude(self):
        return math.hypot(self.x, self.y)

    def magnitude_sq(self):
        return self.x * self.x + self.y * self.y

    def normalizado(self):
        mag = self.magnitude()
        if mag > 0:
            return Vetor2D(self.x / mag, self.y / mag)
        return Vetor2D(0, 0)

    def normalizar(self):
        mag = self.magnitude()
        if mag > 0:
            self.x /= mag
            self.y /= mag
        return self

    def produto_escalar(self, outro):
        return self.x * outro.x + self.y * outro.y

    def distancia(self, outro):
        return math.hypot(self.x - outro.x, self.y - outro.y)

    def angulo(self):
        return math.atan2(self.y, self.x)

    def rotacionar(self, angulo):
        c = math.cos(angulo)
        s = math.sin(angulo)
        return Vetor2D(self.x * c - self.y * s, self.x * s + self.y * c)

    def limitacao(self, max_mag):
        if self.magnitude_sq() > max_mag * max_mag:
            return self.normalizado() * max_mag
        return self

    def copia(self):
        return Vetor2D(self.x, self.y)

    def __repr__(self):
        return f"Vetor2D({self.x}, {self.y})"


class Corpo:
    """Corpo físico com posição, velocidade, massa."""

    def __init__(self, x=0, y=0, massa=1.0, raio=10):
        self.pos = Vetor2D(x, y)
        self.vel = Vetor2D(0, 0)
        self.acel = Vetor2D(0, 0)
        self.forca = Vetor2D(0, 0)
        self.massa = float(massa)
        self.massa_inv = 1.0 / massa if massa > 0 else 0
        self.raio = float(raio)
        self.elasticidade = 0.5  # restituição
        self.atrito = 0.99
        self.estatico = False
        self._callbacks_colisao = []

    def aplicar_forca(self, forca):
        if not self.estatico:
            self.forca += forca

    def aplicar_impulso(self, impulso):
        if not self.estatico:
            self.vel += impulso * self.massa_inv

    def atualizar(self, dt):
        if self.estatico:
            return
        # F = ma -> a = F/m
        self.acel = self.forca * self.massa_inv
        self.vel += self.acel * dt
        self.vel *= self.atrito
        self.pos += self.vel * dt
        self.forca = Vetor2D(0, 0)

    def colidir_com(self, outro):
        """Verifica colisão circular e resolve."""
        if self.estatico and outro.estatico:
            return False

        diff = self.pos - outro.pos
        dist = diff.magnitude()
        raio_soma = self.raio + outro.raio

        if dist >= raio_soma or dist == 0:
            return False

        # Normal da colisão
        normal = diff / dist
        sobreposicao = raio_soma - dist

        # Separar corpos
        if not self.estatico and not outro.estatico:
            self.pos += normal * (sobreposicao * 0.5)
            outro.pos -= normal * (sobreposicao * 0.5)
        elif not self.estatico:
            self.pos += normal * sobreposicao
        elif not outro.estatico:
            outro.pos -= normal * sobreposicao

        # Resolver velocidade (impulso)
        vel_rel = self.vel - outro.vel
        vel_normal = vel_rel.produto_escalar(normal)

        if vel_normal > 0:
            return True  # Já se afastando

        e = min(self.elasticidade, outro.elasticidade)
        j = -(1 + e) * vel_normal
        j /= self.massa_inv + outro.massa_inv

        impulso = normal * j

        if not self.estatico:
            self.vel += impulso * self.massa_inv
        if not outro.estatico:
            outro.vel -= impulso * outro.massa_inv

        # Callbacks
        for cb in self._callbacks_colisao:
            cb(outro)
        for cb in outro._callbacks_colisao:
            cb(self)

        return True

    def ao_colidir(self, callback):
        self._callbacks_colisao.append(callback)


class MundoFisica:
    """Mundo de física com gravidade e corpos."""

    def __init__(self, gravidade_x=0, gravidade_y=9.8):
        self.gravidade = Vetor2D(gravidade_x, gravidade_y)
        self.corpos = []
        self._limites = None  # (x, y, largura, altura)

    def adicionar(self, corpo):
        self.corpos.append(corpo)
        return corpo

    def remover(self, corpo):
        if corpo in self.corpos:
            self.corpos.remove(corpo)

    def definir_limites(self, x, y, largura, altura):
        self._limites = (x, y, largura, altura)

    def atualizar(self, dt, iteracoes=4):
        # Aplicar gravidade
        for corpo in self.corpos:
            if not corpo.estatico:
                corpo.aplicar_forca(self.gravidade * corpo.massa)

        # Atualizar posições
        for corpo in self.corpos:
            corpo.atualizar(dt)

        # Colisões (broad phase simples)
        for i in range(len(self.corpos)):
            for j in range(i + 1, len(self.corpos)):
                self.corpos[i].colidir_com(self.corpos[j])

        # Limites da tela
        if self._limites:
            x, y, w, h = self._limites
            for corpo in self.corpos:
                if not corpo.estatico:
                    # Esquerda
                    if corpo.pos.x - corpo.raio < x:
                        corpo.pos.x = x + corpo.raio
                        corpo.vel.x *= -corpo.elasticidade
                    # Direita
                    if corpo.pos.x + corpo.raio > x + w:
                        corpo.pos.x = x + w - corpo.raio
                        corpo.vel.x *= -corpo.elasticidade
                    # Topo
                    if corpo.pos.y - corpo.raio < y:
                        corpo.pos.y = y + corpo.raio
                        corpo.vel.y *= -corpo.elasticidade
                    # Baixo
                    if corpo.pos.y + corpo.raio > y + h:
                        corpo.pos.y = y + h - corpo.raio
                        corpo.vel.y *= -corpo.elasticidade

    def raio_cast(self, origem, direcao, max_dist, ignorar=None):
        """Raycast simples - retorna primeiro corpo atingido."""
        dir_norm = direcao.normalizado()
        mais_proximo = None
        menor_dist = max_dist

        for corpo in self.corpos:
            if corpo is ignorar:
                continue
            # Colisão raio-círculo
            oc = corpo.pos - origem
            proj = oc.produto_escalar(dir_norm)
            if proj < 0:
                continue
            perp_sq = oc.magnitude_sq() - proj * proj
            raio_sq = corpo.raio * corpo.raio
            if perp_sq <= raio_sq:
                dist_centro = math.sqrt(raio_sq - perp_sq)
                dist_impacto = proj - dist_centro
                if 0 <= dist_impacto < menor_dist:
                    menor_dist = dist_impacto
                    mais_proximo = corpo

        return mais_proximo, menor_dist


class NAgamePhysics:
    """Interface principal do sistema de física."""

    def __init__(self, gravidade_x=0, gravidade_y=500):  # pixels/s^2
        self.mundo = MundoFisica(gravidade_x, gravidade_y)

    def criar_corpo(self, x, y, massa=1, raio=10, estatico=False):
        corpo = Corpo(x, y, massa, raio)
        corpo.estatico = estatico
        self.mundo.adicionar(corpo)
        return corpo

    def criar_retangulo(self, x, y, largura, altura, massa=1, estatico=False):
        # Aproximar como círculo com raio = metade da diagonal
        raio = math.hypot(largura, altura) / 2
        return self.criar_corpo(x + largura/2, y + altura/2, massa, raio, estatico)

    def atualizar(self, dt):
        self.mundo.atualizar(dt)

    def definir_gravidade(self, x, y):
        self.mundo.gravidade = Vetor2D(x, y)

    def definir_limites(self, x, y, largura, altura):
        self.mundo.definir_limites(x, y, largura, altura)

    def raio_cast(self, x, y, angulo, max_dist, ignorar=None):
        origem = Vetor2D(x, y)
        direcao = Vetor2D(math.cos(angulo), math.sin(angulo))
        return self.mundo.raio_cast(origem, direcao, max_dist, ignorar)

    # Helpers para compatibilidade com NA
    def vetor(self, x, y):
        return Vetor2D(x, y)