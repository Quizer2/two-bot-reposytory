"""
Moduł pomocniczy do obsługi asyncio w PyQt

Zapewnia prawidłową integrację pętli zdarzeń asyncio z PyQt
"""

import asyncio
import threading
from typing import Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor

try:
    from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


class AsyncWorker(QThread):
    """Worker thread do wykonywania zadań asyncio"""
    
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, coro, parent=None):
        super().__init__(parent)
        self.coro = coro
        self.result = None
        # Przechowuj referencje do loopa i taska, aby umożliwić łagodne zatrzymanie
        self.loop = None
        self.task = None
        
    def run(self):
        """Uruchamia coroutine w nowej pętli zdarzeń"""
        try:
            # Uruchom coroutine w dedykowanej pętli przez asyncio.run z dostępem do loopa
            async def _runner():
                try:
                    # Pozyskaj działającą pętlę utworzoną przez asyncio.run
                    self.loop = asyncio.get_running_loop()
                    # Utwórz task z coroutine, aby można było go anulować z zewnątrz
                    self.task = self.loop.create_task(self.coro)
                    self.result = await self.task
                    return self.result
                except asyncio.CancelledError:
                    # Task został anulowany
                    raise
            try:
                self.result = asyncio.run(_runner())
                self.finished.emit(self.result)
            except asyncio.CancelledError:
                self.error.emit("Cancelled")
            except Exception as e:
                self.error.emit(str(e))
            finally:
                # Upewnij się, że referencje są zwalniane
                self.loop = None
                self.task = None
        except Exception:
            # Zabezpieczenie przed nieprzewidzianymi wyjątkami
            self.loop = None
            self.task = None
    
    def stop(self):
        """Łagodnie zatrzymuje wykonywaną coroutine"""
        try:
            # Anuluj task jeśli trwa
            if self.task and not self.task.done():
                def _cancel():
                    try:
                        self.task.cancel()
                    except Exception:
                        pass
                try:
                    # Bezpiecznie wywołaj anulowanie w wątku pętli
                    if self.loop:
                        self.loop.call_soon_threadsafe(_cancel)
                except Exception:
                    pass
        except Exception:
            pass

    def __del__(self):
        """Zapewnia bezpieczne zatrzymanie wątku przy niszczeniu obiektu.
        Chroni przed ostrzeżeniem: 'QThread: Destroyed while thread is still running'."""
        try:
            # Spróbuj łagodnego zatrzymania, bez blokowania wątku na samym sobie
            try:
                if hasattr(self, 'stop'):
                    self.stop()
            except Exception:
                pass

            # Nigdy nie wywołuj wait() z wnętrza tego samego wątku – powoduje freeze
            try:
                from PyQt6.QtCore import QThread
                current = QThread.currentThread()
                if current is not self:
                    # Poczekaj krótko na zakończenie, tylko jeśli wywołane z innego wątku
                    self.wait(500)
            except Exception:
                # Jeśli API niedostępne lub sprawdzenie się nie powiodło, nie blokuj
                pass

            # Ostatecznie spróbuj przerwać bez blokowania
            try:
                if self.isRunning():
                    # Preferuj łagodne przerwanie; avoid terminate() gdy to możliwe
                    if hasattr(self, 'requestInterruption'):
                        self.requestInterruption()
            except Exception:
                pass
        except Exception:
            # Ostateczny bezpiecznik – nie propaguj wyjątku z destruktora
            pass


class AsyncManager(QObject):
    """Menedżer zadań asyncio dla PyQt"""
    
    task_finished = pyqtSignal(str, object)
    task_error = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.workers = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def run_async(self, coro, task_id: str = None):
        """Uruchamia coroutine asynchronicznie"""
        if task_id is None:
            task_id = f"task_{id(coro)}"
        
        # Jeśli istnieje już worker dla tego task_id, anuluj go aby uniknąć osieroconych wątków
        if task_id in self.workers:
            try:
                self.cancel_task(task_id)
            except Exception:
                pass
            
        worker = AsyncWorker(coro)
        worker.finished.connect(lambda result: self._on_task_finished(task_id, result))
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(lambda error: self._on_task_error(task_id, error))
        worker.error.connect(worker.deleteLater)
        
        self.workers[task_id] = worker
        worker.start()
        
        return task_id
    
    def _on_task_finished(self, task_id: str, result: Any):
        """Obsługuje zakończenie zadania"""
        if task_id in self.workers:
            del self.workers[task_id]
        self.task_finished.emit(task_id, result)
    
    def _on_task_error(self, task_id: str, error: str):
        """Obsługuje błąd zadania"""
        if task_id in self.workers:
            del self.workers[task_id]
        self.task_error.emit(task_id, error)
    
    def cancel_task(self, task_id: str):
        """Anuluje zadanie"""
        if task_id in self.workers:
            worker = self.workers[task_id]
            try:
                # Najpierw spróbuj łagodnego zatrzymania
                if hasattr(worker, 'stop'):
                    worker.stop()
                from PyQt6.QtCore import QThread
                # Unikaj oczekiwania na samego siebie, co powoduje komunikat 'QThread::wait: Thread tried to wait on itself'
                current = QThread.currentThread()
                if current is not worker:
                    # Poczekaj na zakończenie
                    worker.wait(500)
                    # Jeśli nadal działa, wymuś zakończenie
                    if worker.isRunning():
                        worker.terminate()
                        worker.wait(500)
                else:
                    # Jeżeli anulujemy z tego samego wątku, użyj przerwania bez blokowania
                    if hasattr(worker, 'requestInterruption'):
                        worker.requestInterruption()
            except Exception:
                # W ostateczności wymuś zakończenie
                try:
                    worker.terminate()
                    # Nie wywołuj wait bez sprawdzenia kontekstu
                except Exception:
                    pass
            finally:
                del self.workers[task_id]
    
    def cleanup(self):
        """Czyści wszystkie zadania"""
        for task_id in list(self.workers.keys()):
            self.cancel_task(task_id)
        self.executor.shutdown(wait=True)


class BotAsyncManager(QObject):
    """Specjalny menedżer dla botów handlowych"""
    
    bot_started = pyqtSignal(str)
    bot_stopped = pyqtSignal(str)
    bot_error = pyqtSignal(str, str)
    bot_status_updated = pyqtSignal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.async_manager = AsyncManager(self)
        self.running_bots = {}
        self.bot_loops = {}
        
        # Połącz sygnały
        self.async_manager.task_finished.connect(self._on_bot_task_finished)
        self.async_manager.task_error.connect(self._on_bot_task_error)
        
        # Timer do monitorowania statusu
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_bots_status)
        self.status_timer.start(5000)  # Co 5 sekund
    
    def start_bot(self, bot, bot_name: str):
        """Uruchamia bota asynchronicznie"""
        if bot_name in self.running_bots:
            print(f"Bot {bot_name} już działa")
            return
        
        # Utwórz coroutine dla bota
        async def bot_runner():
            try:
                await bot.start()
            except Exception as e:
                print(f"Błąd bota {bot_name}: {e}")
                raise
        
        task_id = f"bot_{bot_name}"
        self.running_bots[bot_name] = bot
        self.async_manager.run_async(bot_runner(), task_id)
        
        print(f"🚀 Uruchamianie bota: {bot_name}")
    
    def stop_bot(self, bot_name: str):
        """Zatrzymuje bota"""
        if bot_name not in self.running_bots:
            print(f"Bot {bot_name} nie działa")
            return
        
        bot = self.running_bots[bot_name]
        
        # Utwórz coroutine do zatrzymania
        async def bot_stopper():
            try:
                await bot.stop()
            except Exception as e:
                print(f"Błąd zatrzymywania bota {bot_name}: {e}")
                raise
        
        task_id = f"stop_bot_{bot_name}"
        self.async_manager.run_async(bot_stopper(), task_id)
        
        print(f"🛑 Zatrzymywanie bota: {bot_name}")
    
    def _on_bot_task_finished(self, task_id: str, result: Any):
        """Obsługuje zakończenie zadania bota"""
        if task_id.startswith("bot_"):
            bot_name = task_id[4:]  # Usuń prefix "bot_"
            if bot_name in self.running_bots:
                del self.running_bots[bot_name]
            self.bot_stopped.emit(bot_name)
            print(f"✅ Bot {bot_name} zakończył pracę")
        
        elif task_id.startswith("stop_bot_"):
            bot_name = task_id[9:]  # Usuń prefix "stop_bot_"
            if bot_name in self.running_bots:
                del self.running_bots[bot_name]
            self.bot_stopped.emit(bot_name)
            print(f"🛑 Bot {bot_name} zatrzymany")
    
    def _on_bot_task_error(self, task_id: str, error: str):
        """Obsługuje błędy botów"""
        if task_id.startswith("bot_") or task_id.startswith("stop_bot_"):
            bot_name = task_id.split("_", 1)[1] if "_" in task_id else task_id
            if bot_name in self.running_bots:
                del self.running_bots[bot_name]
            self.bot_error.emit(bot_name, error)
            print(f"❌ Błąd bota {bot_name}: {error}")
    
    def _update_bots_status(self):
        """Aktualizuje status botów"""
        for bot_name, bot in self.running_bots.items():
            status = {
                'running': bot.is_running if hasattr(bot, 'is_running') else True,
                'symbol': getattr(bot, 'symbol', 'N/A'),
                'strategy': getattr(bot.strategy, 'name', 'N/A') if hasattr(bot, 'strategy') else 'N/A',
                'positions': len(getattr(bot, 'positions', [])),
                'orders': len(getattr(bot, 'orders', [])),
                'pnl': getattr(bot, 'pnl', 0.0)
            }
            self.bot_status_updated.emit(bot_name, status)
    
    def get_running_bots(self):
        """Zwraca listę działających botów"""
        return list(self.running_bots.keys())
    
    def is_bot_running(self, bot_name: str):
        """Sprawdza czy bot działa"""
        return bot_name in self.running_bots
    
    def cleanup(self):
        """Czyści wszystkie boty"""
        # Zatrzymaj timer
        self.status_timer.stop()
        
        # Zatrzymaj wszystkie boty
        for bot_name in list(self.running_bots.keys()):
            self.stop_bot(bot_name)
        
        # Wyczyść async manager
        self.async_manager.cleanup()


# Singleton instance
_async_manager = None
_bot_async_manager = None

def get_async_manager():
    """Zwraca singleton AsyncManager"""
    global _async_manager
    if _async_manager is None:
        _async_manager = AsyncManager()
    return _async_manager

def get_bot_async_manager():
    """Zwraca singleton BotAsyncManager"""
    global _bot_async_manager
    if _bot_async_manager is None:
        _bot_async_manager = BotAsyncManager()
    return _bot_async_manager