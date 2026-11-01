"""
NAgame Audio Backend - Sistema de áudio usando Pygame
"""

import pygame
import os


class NAgameAudio:
    """Sistema de áudio para música e efeitos sonoros."""

    def __init__(self):
        self._sons = {}
        self._musica_atual = None
        self._volume_musica = 0.5
        self._volume_efeitos = 0.7
        self._canais = {}
        self._inicializado = False

    def iniciar(self, frequencia=44100, tamanho=-16, canais=2, buffer=512):
        """Inicializa o mixer de áudio."""
        try:
            pygame.mixer.pre_init(frequencia, tamanho, canais, buffer)
            pygame.mixer.init()
            self._inicializado = True
            # Reservar canais para efeitos
            pygame.mixer.set_reserved(8)
            return True
        except Exception as e:
            print(f"Erro ao inicializar áudio: {e}")
            return False

    # --- Música ---
    def carregar_musica(self, caminho, nome=None):
        """Carrega arquivo de música (streaming)."""
        if not self._inicializado:
            self.iniciar()
        try:
            if nome is None:
                nome = os.path.basename(caminho)
            self._sons[nome] = {"tipo": "musica", "caminho": caminho}
            return nome
        except Exception as e:
            print(f"Erro ao carregar música {caminho}: {e}")
            return None

    def tocar_musica(self, nome, loops=-1, fade_in=0):
        """Toca música carregada."""
        if nome not in self._sons:
            print(f"Música não carregada: {nome}")
            return
        if self._sons[nome]["tipo"] != "musica":
            print(f"Não é música: {nome}")
            return
        try:
            pygame.mixer.music.load(self._sons[nome]["caminho"])
            pygame.mixer.music.set_volume(self._volume_musica)
            pygame.mixer.music.play(loops, fade_ms=fade_in)
            self._musica_atual = nome
        except Exception as e:
            print(f"Erro ao tocar música: {e}")

    def pausar_musica(self):
        pygame.mixer.music.pause()

    def despausar_musica(self):
        pygame.mixer.music.unpause()

    def parar_musica(self, fade_out=0):
        pygame.mixer.music.fadeout(fade_out) if fade_out > 0 else pygame.mixer.music.stop()
        self._musica_atual = None

    def definir_volume_musica(self, volume):
        self._volume_musica = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self._volume_musica)

    # --- Efeitos Sonoros (Sound) ---
    def carregar_som(self, caminho, nome=None):
        """Carrega efeito sonoro (em memória)."""
        if not self._inicializado:
            self.iniciar()
        try:
            if nome is None:
                nome = os.path.basename(caminho)
            som = pygame.mixer.Sound(caminho)
            som.set_volume(self._volume_efeitos)
            self._sons[nome] = {"tipo": "som", "objeto": som}
            return nome
        except Exception as e:
            print(f"Erro ao carregar som {caminho}: {e}")
            return None

    def tocar_som(self, nome, loops=0, fade_in=0, canal=None):
        """Toca efeito sonoro."""
        if nome not in self._sons:
            print(f"Som não carregado: {nome}")
            return None
        if self._sons[nome]["tipo"] != "som":
            print(f"Não é efeito sonoro: {nome}")
            return None

        som = self._sons[nome]["objeto"]
        try:
            if canal is not None:
                ch = pygame.mixer.Channel(canal)
                ch.play(som, loops, fade_ms=fade_in)
                self._canais[canal] = ch
                return canal
            else:
                ch = som.play(loops, fade_ms=fade_in)
                return ch
        except Exception as e:
            print(f"Erro ao tocar som: {e}")
            return None

    def parar_som(self, nome):
        """Para todas as instâncias de um som."""
        if nome in self._sons and self._sons[nome]["tipo"] == "som":
            self._sons[nome]["objeto"].stop()

    def definir_volume_som(self, nome, volume):
        if nome in self._sons and self._sons[nome]["tipo"] == "som":
            self._sons[nome]["objeto"].set_volume(max(0.0, min(1.0, volume)))

    # --- Canais ---
    def canal_ocupado(self, canal):
        if canal in self._canais:
            return self._canais[canal].get_busy()
        return pygame.mixer.Channel(canal).get_busy()

    def parar_canal(self, canal):
        if canal in self._canais:
            self._canais[canal].stop()
        else:
            pygame.mixer.Channel(canal).stop()

    def definir_volume_canal(self, canal, volume):
        if canal in self._canais:
            self._canais[canal].set_volume(max(0.0, min(1.0, volume)))
        else:
            pygame.mixer.Channel(canal).set_volume(max(0.0, min(1.0, volume)))

    def fila_canal(self, canal, nome_som):
        """Adiciona som à fila do canal."""
        if nome_som in self._sons and self._sons[nome_som]["tipo"] == "som":
            if canal in self._canais:
                self._canais[canal].queue(self._sons[nome_som]["objeto"])
            else:
                pygame.mixer.Channel(canal).queue(self._sons[nome_som]["objeto"])

    # --- Volume Global ---
    def definir_volume_efeitos(self, volume):
        self._volume_efeitos = max(0.0, min(1.0, volume))
        for info in self._sons.values():
            if info["tipo"] == "som":
                info["objeto"].set_volume(self._volume_efeitos)

    # --- Utilitários ---
    def musica_tocando(self):
        return pygame.mixer.music.get_busy()

    def obter_pos_musica(self):
        return pygame.mixer.music.get_pos() / 1000.0  # em segundos

    def limpar(self):
        """Libera recursos."""
        self.parar_musica()
        for info in self._sons.values():
            if info["tipo"] == "som":
                info["objeto"] = None
        self._sons.clear()
        self._canais.clear()
        pygame.mixer.quit()
        self._inicializado = False