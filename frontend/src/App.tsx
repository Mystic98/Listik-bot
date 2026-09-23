import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type User = {
  telegram_id: number;
  username?: string;
  full_name: string;
  status: "approved" | "pending" | "not_registered";
  is_admin: boolean;
};

type Room = {
  id: number;
  name: string;
  is_creator: boolean;
  is_active: boolean;
};

type Item = {
  id: number;
  name: string;
  quantity?: string;
  category: string;
  is_purchased: boolean;
  version: number;
};

type Category = { id: string; name: string };

const telegram = window.Telegram?.WebApp;
const initData = telegram?.initData ?? import.meta.env.VITE_DEV_INIT_DATA ?? "";

function api(path: string, options: RequestInit = {}) {
  return fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${initData}`,
      ...(options.headers ?? {}),
    },
  });
}

function parseQuickInput(value: string): { name: string; quantity?: string } {
  const match = value.trim().match(/^(.+?)\s+(\d+(?:[.,]\d+)?\s*(?:кг|г|л|мл|шт|уп))$/i);
  if (!match) return { name: value.trim() };
  return { name: match[1].trim(), quantity: match[2].replace(",", ".") };
}

function categoryTitle(category: string, categories: Category[]) {
  return categories.find((item) => item.id === category)?.name ?? "📦 Другое";
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [activeRoomId, setActiveRoomId] = useState<number | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [quickInput, setQuickInput] = useState("");
  const [pendingCategoryItem, setPendingCategoryItem] = useState<Item | null>(null);
  const [editingItem, setEditingItem] = useState<Item | null>(null);
  const [tab, setTab] = useState("list");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadItems = useCallback(async (roomId: number) => {
    const response = await api(`/api/v1/rooms/${roomId}/items`);
    if (!response.ok) throw new Error("Не удалось загрузить список");
    const data = (await response.json()) as { items: Item[] };
    setItems(data.items);
  }, []);

  const loadApp = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const meResponse = await api("/api/v1/me");
      if (!meResponse.ok) throw new Error("Не удалось проверить доступ");
      const me = (await meResponse.json()) as User;
      setUser(me);
      if (me.status !== "approved") return;

      const [roomsResponse, categoriesResponse] = await Promise.all([
        api("/api/v1/rooms"),
        api("/api/v1/categories"),
      ]);
      if (!roomsResponse.ok || !categoriesResponse.ok) throw new Error("Не удалось загрузить данные");
      const roomsData = (await roomsResponse.json()) as { rooms: Room[]; active_room_id: number | null };
      setRooms(roomsData.rooms);
      setCategories((await categoriesResponse.json()) as Category[]);
      const roomId = roomsData.active_room_id ?? roomsData.rooms[0]?.id ?? null;
      setActiveRoomId(roomId);
      if (roomId) await loadItems(roomId);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Неизвестная ошибка");
    } finally {
      setLoading(false);
    }
  }, [loadItems]);

  useEffect(() => {
    telegram?.ready();
    telegram?.expand();
    void loadApp();
  }, [loadApp]);

  useEffect(() => {
    if (!activeRoomId || !initData || user?.status !== "approved") return;
    let closed = false;
    let retryDelay = 1000;
    let retryTimer: number | undefined;
    let socket: WebSocket | undefined;
    const connect = () => {
      if (closed) return;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${window.location.host}/ws/rooms/${activeRoomId}`);
      socket.onopen = () => {
        retryDelay = 1000;
        socket?.send(JSON.stringify({ init_data: initData }));
      };
      socket.onmessage = () => void loadItems(activeRoomId);
      socket.onclose = () => {
        if (closed) return;
        retryTimer = window.setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 30000);
      };
    };
    connect();
    return () => {
      closed = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, [activeRoomId, loadItems, user?.status]);

  const activeItems = useMemo(() => items.filter((item) => !item.is_purchased), [items]);
  const purchasedItems = useMemo(() => items.filter((item) => item.is_purchased), [items]);
  const groups = useMemo(() => {
    const grouped = new Map<string, Item[]>();
    activeItems.forEach((item) => grouped.set(item.category, [...(grouped.get(item.category) ?? []), item]));
    return [...grouped.entries()];
  }, [activeItems]);

  async function submitItem(event: FormEvent) {
    event.preventDefault();
    if (!activeRoomId || !quickInput.trim()) return;
    setBusy(true);
    setError("");
    try {
      const parsed = parseQuickInput(quickInput);
      const response = await api(`/api/v1/rooms/${activeRoomId}/items`, {
        method: "POST",
        body: JSON.stringify(parsed),
      });
      if (!response.ok) throw new Error("Не удалось добавить товар");
      const result = (await response.json()) as { item: Item; merged: boolean; needs_category: boolean };
      setQuickInput("");
      setNotice(result.merged ? "Количество объединено" : "Товар добавлен");
      if (result.needs_category) setPendingCategoryItem(result.item);
      await loadItems(activeRoomId);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Неизвестная ошибка");
    } finally {
      setBusy(false);
    }
  }

  async function togglePurchased(item: Item) {
    if (!activeRoomId) return;
    setBusy(true);
    try {
      const action = item.is_purchased ? "unpurchase" : "purchase";
      const response = await api(`/api/v1/rooms/${activeRoomId}/items/${item.id}/${action}`, { method: "POST" });
      if (!response.ok) throw new Error("Товар уже изменён другим участником");
      await loadItems(activeRoomId);
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : "Неизвестная ошибка");
      await loadItems(activeRoomId);
    } finally {
      setBusy(false);
    }
  }

  async function setCategory(category: string) {
    if (!activeRoomId || !pendingCategoryItem) return;
    const response = await api(`/api/v1/rooms/${activeRoomId}/items/${pendingCategoryItem.id}/category`, {
      method: "PATCH",
      body: JSON.stringify({ category }),
    });
    if (!response.ok) {
      setError("Не удалось сохранить категорию");
      return;
    }
    setPendingCategoryItem(null);
    await loadItems(activeRoomId);
  }

  async function saveItem(name: string, quantity: string, category: string) {
    if (!activeRoomId || !editingItem) return;
    setBusy(true);
    try {
      const response = await api(`/api/v1/rooms/${activeRoomId}/items/${editingItem.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name,
          quantity: quantity || null,
          category,
          version: editingItem.version,
        }),
      });
      if (response.status === 409) throw new Error("Товар уже изменён другим участником");
      if (!response.ok) throw new Error("Не удалось сохранить товар");
      setEditingItem(null);
      setNotice("Изменения сохранены");
      await loadItems(activeRoomId);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Неизвестная ошибка");
    } finally {
      setBusy(false);
    }
  }

  async function removeItem(item: Item) {
    if (!activeRoomId || !window.confirm(`Удалить «${item.name}»?`)) return;
    setBusy(true);
    try {
      const response = await api(`/api/v1/rooms/${activeRoomId}/items/${item.id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Не удалось удалить товар");
      setEditingItem(null);
      setNotice("Товар удалён");
      await loadItems(activeRoomId);
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "Неизвестная ошибка");
    } finally {
      setBusy(false);
    }
  }

  async function activateRoom(roomId: number) {
    if (roomId === activeRoomId) return;
    setBusy(true);
    try {
      const response = await api(`/api/v1/rooms/${roomId}/activate`, { method: "POST" });
      if (!response.ok) throw new Error("Не удалось переключить комнату");
      const data = (await response.json()) as { rooms: Room[]; active_room_id: number | null };
      setRooms(data.rooms);
      setActiveRoomId(data.active_room_id);
      if (data.active_room_id) await loadItems(data.active_room_id);
      setTab("list");
      setNotice("Комната переключена");
    } catch (activateError) {
      setError(activateError instanceof Error ? activateError.message : "Неизвестная ошибка");
    } finally {
      setBusy(false);
    }
  }

  if (!initData) {
    return <StatusScreen title="Откройте Листочек в Telegram" text="Mini App получает доступ только из Telegram." />;
  }
  if (loading) return <div className="loading">Загружаем список…</div>;
  if (user?.status === "pending") {
    return <StatusScreen title="Заявка на проверке" text="Администратор ещё не одобрил доступ к общим спискам." />;
  }
  if (user?.status === "not_registered") {
    return <StatusScreen title="Сначала запустите бота" text="Отправьте /start в чате с Листочком, затем откройте Mini App снова." />;
  }
  if (!activeRoomId) {
    return <StatusScreen title="Нет активной комнаты" text="Создайте или выберите комнату в Telegram-боте." />;
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <span className="eyebrow">ЛИСТОЧЕК</span>
          <h1>{rooms.find((room) => room.id === activeRoomId)?.name ?? "Список покупок"}</h1>
        </div>
        <span className="count-badge">{activeItems.length}</span>
      </header>

      {error && <div className="alert error">{error}</div>}
      {notice && <button className="alert notice" onClick={() => setNotice("")}>{notice}</button>}

      {tab === "list" && (
        <>
          <form className="quick-add" onSubmit={submitItem}>
            <span className="plus">＋</span>
            <input value={quickInput} onChange={(event) => setQuickInput(event.target.value)} placeholder="Добавить продукт, например молоко 2л" />
            <button disabled={busy || !quickInput.trim()} type="submit">Добавить</button>
          </form>

          <section className="list-section">
            {groups.length === 0 && <div className="empty-card"><span>✨</span><strong>Список пуст</strong><p>Добавьте первый продукт — и он появится здесь.</p></div>}
            {groups.map(([category, categoryItems]) => (
              <div className="category-group" key={category}>
                <h2>{categoryTitle(category, categories)}</h2>
                {categoryItems.map((item) => <ItemRow item={item} onToggle={togglePurchased} onEdit={setEditingItem} key={item.id} />)}
              </div>
            ))}
            {purchasedItems.length > 0 && (
              <details className="purchased-group">
                <summary>Куплено <span>{purchasedItems.length}</span></summary>
                {purchasedItems.map((item) => <ItemRow item={item} onToggle={togglePurchased} onEdit={setEditingItem} key={item.id} />)}
              </details>
            )}
          </section>
        </>
      )}

      {tab === "rooms" && <RoomsPanel rooms={rooms} activeRoomId={activeRoomId} busy={busy} onSelect={activateRoom} />}
      {tab === "templates" && <div className="empty-card secondary"><span>🧺</span><strong>Шаблоны доступны в боте</strong><p>Мы подключим управление шаблонами в Mini App следующим срезом, сохранив текущие шаблоны и правила конфликтов.</p></div>}
      {tab === "more" && <div className="empty-card secondary"><span>✨</span><strong>Листочек растёт</strong><p>Администрирование и приглашения пока остаются в Telegram-боте.</p></div>}

      <nav className="bottom-nav">
        <NavButton active={tab === "list"} icon="🛒" label="Список" onClick={() => setTab("list")} />
        <NavButton active={tab === "templates"} icon="🧺" label="Шаблоны" onClick={() => setTab("templates")} />
        <NavButton active={tab === "rooms"} icon="🏠" label="Комнаты" onClick={() => setTab("rooms")} />
        <NavButton active={tab === "more"} icon="•••" label="Ещё" onClick={() => setTab("more")} />
      </nav>

      {pendingCategoryItem && (
        <div className="modal-backdrop" onClick={() => setPendingCategoryItem(null)}>
          <div className="category-modal" onClick={(event) => event.stopPropagation()}>
            <span className="eyebrow">УТОЧНИМ</span>
            <h2>Куда положить «{pendingCategoryItem.name}»?</h2>
            <p>Мы не уверены в категории. Выберите отдел — это поможет сортировать список.</p>
            <div className="category-options">{categories.map((category) => <button key={category.id} onClick={() => void setCategory(category.id)}>{category.name}</button>)}</div>
          </div>
        </div>
      )}

      {editingItem && (
        <EditItemModal
          item={editingItem}
          categories={categories}
          busy={busy}
          onClose={() => setEditingItem(null)}
          onSave={saveItem}
          onDelete={() => void removeItem(editingItem)}
        />
      )}
    </main>
  );
}

function ItemRow({ item, onToggle, onEdit }: { item: Item; onToggle: (item: Item) => void; onEdit: (item: Item) => void }) {
  return <div className={`item-row ${item.is_purchased ? "purchased" : ""}`}><button className="item-main" onClick={() => onToggle(item)}><span className="check">{item.is_purchased ? "✓" : ""}</span><span className="item-name">{item.name}</span>{item.quantity && <span className="quantity">{item.quantity}</span>}</button><button className="edit-button" aria-label={`Изменить ${item.name}`} onClick={() => onEdit(item)}>•••</button></div>;
}

function NavButton({ active, icon, label, onClick }: { active: boolean; icon: string; label: string; onClick: () => void }) {
  return <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}><span>{icon}</span>{label}</button>;
}

function StatusScreen({ title, text }: { title: string; text: string }) {
  return <main className="status-screen"><div className="logo-mark">Л</div><span className="eyebrow">ЛИСТОЧЕК</span><h1>{title}</h1><p>{text}</p></main>;
}

function RoomsPanel({ rooms, activeRoomId, busy, onSelect }: { rooms: Room[]; activeRoomId: number; busy: boolean; onSelect: (roomId: number) => void }) {
  return <section className="rooms-panel"><span className="eyebrow">ПРОСТРАНСТВА</span><h2>Ваши комнаты</h2><p>Список покупок и шаблоны разделены между комнатами.</p>{rooms.map((room) => <button className={`room-card ${room.id === activeRoomId ? "active" : ""}`} key={room.id} disabled={busy} onClick={() => void onSelect(room.id)}><span className="room-icon">🏠</span><span><strong>{room.name}</strong><small>{room.is_creator ? "Вы создатель" : "Участник"}</small></span><span className="room-arrow">{room.id === activeRoomId ? "✓" : "›"}</span></button>)}</section>;
}

function EditItemModal({ item, categories, busy, onClose, onSave, onDelete }: { item: Item; categories: Category[]; busy: boolean; onClose: () => void; onSave: (name: string, quantity: string, category: string) => void; onDelete: () => void }) {
  const [name, setName] = useState(item.name);
  const [quantity, setQuantity] = useState(item.quantity ?? "");
  const [category, setCategory] = useState(item.category);
  return <div className="modal-backdrop" onClick={onClose}><form className="category-modal edit-modal" onClick={(event) => event.stopPropagation()} onSubmit={(event) => { event.preventDefault(); void onSave(name.trim(), quantity.trim(), category); }}><span className="eyebrow">ТОВАР</span><h2>Изменить продукт</h2><label>Название<input value={name} onChange={(event) => setName(event.target.value)} /></label><label>Количество<input value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="Например, 2 л" /></label><label>Категория<select value={category} onChange={(event) => setCategory(event.target.value)}>{categories.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></label><div className="edit-actions"><button type="button" className="delete-button" onClick={onDelete}>Удалить</button><button type="submit" className="save-button" disabled={busy || !name.trim()}>Сохранить</button></div></form></div>;
}
