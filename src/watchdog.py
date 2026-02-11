import threading
import time

class WatchdogMonitor:
    
    def __init__(self, app):
        self.app = app
        self.active = False
        self.thread = None
        self.last_heartbeat = time.time()
        self.recovery_count = 0
        self.last_recovery_time = 0
        self.max_recoveries = 5
        self.heartbeat_timeout = 30.0
        self.check_interval = 10.0
        
    def start(self):
        if self.active:
            return
        
        self.active = True
        self.last_heartbeat = time.time()
        self.recovery_count = 0
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("🐕 Watchdog started - monitoring for stuck states")
    
    def stop(self):
        self.active = False
    
    def update_heartbeat(self):
        self.last_heartbeat = time.time()
    
    def reset_recovery_count(self):
        self.recovery_count = 0
    
    def _monitor_loop(self):
        while self.active:
            try:
                current_time = time.time()
                heartbeat_age = current_time - self.last_heartbeat
                
                if heartbeat_age > self.heartbeat_timeout:
                    print(f"🚨 WATCHDOG: No heartbeat for {heartbeat_age:.0f}s - Loop appears stuck")
                    self._restart_fishing_loop()
                    break
                
                if self._check_state_timeout():
                    print("🚨 WATCHDOG: State timeout detected - Restarting loop")
                    self._restart_fishing_loop()
                    break
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"⚠️ Watchdog error: {e}")
                time.sleep(self.check_interval)
        
        print("🐕 Watchdog monitor loop ended")
    
    def _check_state_timeout(self):
        if not hasattr(self.app, 'state_start_time'):
            return False
        
        current_time = time.time()
        state_duration = current_time - self.app.state_start_time
        
        max_durations = {
            "idle": 45.0,
            "fishing": 90.0,
            "casting": 20.0,
            "waiting": 35.0,
            "purchasing": 60.0,
            "crafting": 300.0,  # Crafting can take 3-5 minutes with multiple baits
            "pre_cast": 120.0  # Pre-cast includes purchase and crafting
        }
        
        current_state = getattr(self.app, 'current_state', 'idle')
        max_duration = max_durations.get(current_state, 60.0)
        
        if state_duration > max_duration:
            print(f'🚨 State "{current_state}" stuck for {state_duration:.0f}s (max: {max_duration}s)')
            return True
        
        return False
    
    def _restart_fishing_loop(self):
        current_time = time.time()
        
        if self.recovery_count >= self.max_recoveries:
            print(f'🛑 TOO MANY RESTARTS: {self.recovery_count} attempts. Stopping fishing.')
            self.app.running = False
            self.active = False
            return
        
        if current_time - self.last_recovery_time < 5.0:
            print("⚠️ Skipping recovery - too soon after last attempt")
            return
        
        self.recovery_count += 1
        self.last_recovery_time = current_time
        
        print(f'🔄 RESTARTING LOOP #{self.recovery_count}/{self.max_recoveries} - Fishing got stuck')
        
        try:
            if self.app.is_holding_click:
                import ctypes
                ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                self.app.is_holding_click = False
                print("Released stuck mouse click")
        except Exception as e:
            print(f"Error releasing mouse: {e}")
        
        self.app.state_start_time = current_time
        self.last_heartbeat = current_time

        if self.app.auto_buy_common_bait:
            self.app.bait_purchase_loop_counter = self.app.loops_per_purchase
            print("🛒 Bait purchase will trigger on next loop")

        time.sleep(2.0)
        
        print('🐕 Restarting watchdog monitor...')
        self.active = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        if hasattr(self.app, 'send_recovery_webhook'):
            self.app.send_recovery_webhook(self.recovery_count)
        
        print('✅ Recovery complete - fishing should resume')
