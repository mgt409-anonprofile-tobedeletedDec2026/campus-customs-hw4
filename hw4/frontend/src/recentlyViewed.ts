/** Recently viewed products, kept only in this browser (never sent to the server). */

export interface RecentItem {
  product_id: string;
  name: string;
  price: number;
  image_url: string;
}

const KEY = "cc_recently_viewed";
const MAX_ITEMS = 8;
export const RECENT_EVENT = "cc-recent-change";

export function getRecent(): RecentItem[] {
  try {
    const items = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(items) ? items : [];
  } catch {
    return [];
  }
}

export function recordView(item: RecentItem) {
  const items = [item, ...getRecent().filter((i) => i.product_id !== item.product_id)].slice(0, MAX_ITEMS);
  localStorage.setItem(KEY, JSON.stringify(items));
  window.dispatchEvent(new Event(RECENT_EVENT));
}

export function clearRecent() {
  localStorage.removeItem(KEY);
  window.dispatchEvent(new Event(RECENT_EVENT));
}
