/// <reference types="vite/client" />

interface TelegramWebApp {
  initData: string;
  ready: () => void;
  expand: () => void;
  onEvent: (event: string, callback: () => void) => void;
}

interface Window {
  Telegram?: { WebApp: TelegramWebApp };
}
