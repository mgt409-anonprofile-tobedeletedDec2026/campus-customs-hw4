export interface Product {
  product_id: string;
  name: string;
  garment_type: string;
  price: number;
  colors: string[];
  description: string;
  tagline: string;
  image_url: string;
  total_in_stock: number;
  sizes_sold_out: string[];
}

export interface SizeStock {
  size: string;
  quantity: number;
}

export interface ProductDetail extends Product {
  story: string;
  sizes: SizeStock[];
}

export interface ChatProduct {
  product_id: string;
  name: string;
  price: number;
  image_url: string;
}

/** Search results Dan sends for the "Handsome Dan's Picks" section (same shape as catalogue cards). */
export interface PagePicks {
  label: string;
  products: Product[];
}

export interface ChatReply {
  reply: string;
  products: ChatProduct[];
  picks: PagePicks | null;
  signup_invite: boolean;
  facts_checked: number;
  corrected: boolean;
  conversation_id: string;
  ended: boolean;
}

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    throw new Error(res.status === 404 ? "not-found" : `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const fetchProducts = () => getJson<Product[]>("/api/products");

export const fetchProduct = (id: string) =>
  getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`);

export const sendChat = (message: string, conversation_id: string | null, viewing_product_id: string | null) =>
  getJson<ChatReply>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id, viewing_product_id }),
  });

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

/** POST JSON and surface the backend's error message (FastAPI's `detail`) on failure. */
async function postAuth<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.");
  }
  return data as T;
}

export const fetchMe = () => getJson<{ user: User | null }>("/api/auth/me").then((d) => d.user);

export const login = (email: string, password: string) =>
  postAuth<User>("/api/auth/login", { email, password });

export const signup = (fields: {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  confirm_password: string;
}) => postAuth<User>("/api/auth/signup", fields);

export const logout = () => postAuth<{ ok: boolean }>("/api/auth/logout");

export interface BagItem {
  id: number;
  product_id: string;
  name: string;
  size: string;
  quantity: number;
  price: number;
  line_total: number;
  in_stock: number;
  image_url: string;
}

export interface Bag {
  items: BagItem[];
  count: number;
  subtotal: number;
}

async function bagRequest(method: string, url: string, body?: unknown): Promise<Bag> {
  const res = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.");
  }
  return data as Bag;
}

export const fetchBag = () => bagRequest("GET", "/api/cart");
export const addToBag = (product_id: string, size: string, quantity: number) =>
  bagRequest("POST", "/api/cart", { product_id, size, quantity });
export const updateBagItem = (id: number, quantity: number) =>
  bagRequest("PUT", `/api/cart/${id}`, { quantity });
export const removeBagItem = (id: number) => bagRequest("DELETE", `/api/cart/${id}`);

/** Mirrors the backend's rules for new passwords. */
export const PASSWORD_RULES: { label: string; test: (pw: string) => boolean }[] = [
  { label: "At least 12 characters", test: (pw) => pw.length >= 12 },
  { label: "A capital letter", test: (pw) => /[A-Z]/.test(pw) },
  { label: "A lowercase letter", test: (pw) => /[a-z]/.test(pw) },
  { label: "A number", test: (pw) => /\d/.test(pw) },
  { label: "A symbol", test: (pw) => /[^A-Za-z0-9]/.test(pw) },
];

export interface SavedMessage {
  role: "user" | "assistant";
  content: string;
  products: ChatProduct[];
}

/** Saved chat for the logged-in shopper. */
export const fetchChatHistory = () =>
  getJson<{ messages: SavedMessage[] }>("/api/chat/history").then((d) => d.messages);

export const clearChatHistory = () => getJson<{ deleted: number }>("/api/chat/history", { method: "DELETE" });

/** After a guest signs up or logs in, save the chat they already had to their account. */
export const claimChat = (conversation_id: string) =>
  getJson<{ saved: boolean }>("/api/chat/claim", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id }),
  });

export const formatPrice = (price: number) =>
  price.toLocaleString("en-US", { style: "currency", currency: "USD" });

/** Rough garment family, used for the filter chips on the Products page. */
export function garmentFamily(p: Product): string {
  const t = `${p.garment_type} ${p.name}`.toLowerCase();
  if (t.includes("quarter-zip") || t.includes("1/4 zip") || t.includes("1 4 zip")) return "Quarter-zips";
  if (t.includes("jacket") || t.includes("fleece")) return "Outerwear";
  if (t.includes("hood")) return "Hoodies";
  if (t.includes("crew") || t.includes("sweatshirt") || t.includes("mockneck")) return "Crewnecks";
  if (t.includes("long-sleeve") || t.includes("performance")) return "Performance";
  return "Tees";
}

/** The garment's main color (first color listed), grouped into a few families for filtering. */
export const COLOR_FAMILIES = ["Navy", "Gray", "Charcoal", "Cream", "White", "Pink"] as const;

export function garmentColor(p: Product): string | null {
  const c = (p.colors[0] ?? "").toLowerCase();
  if (!c) return null;
  if (c.includes("navy")) return "Navy";
  if (c.includes("charcoal") || c.includes("dark heather")) return "Charcoal";
  if (c.includes("gray") || c.includes("grey")) return "Gray";
  if (c.includes("cream") || c.includes("ivory")) return "Cream";
  if (c.includes("white")) return "White";
  if (c.includes("coral") || c.includes("pink")) return "Pink";
  return null;
}

const RESIDENTIAL_COLLEGES = [
  "benjamin franklin", "berkeley", "branford", "davenport", "ezra stiles", "grace hopper",
  "jonathan edwards", "morse", "pauli murray", "pierson", "saybrook", "silliman",
  "timothy dwight", "trumbull",
];
const SPORTS = [
  "baseball", "basketball", "crew", "diving", "fencing", "field hockey", "football", "golf",
  "hockey", "lacrosse", "sailing", "soccer", "squash", "swimming", "tennis", "track", "volleyball",
];
const FAMILY = ["mom", "dad", "aunt", "uncle", "grandma", "grandpa", "brother", "cousin"];

const hasWord = (text: string, words: string[]) =>
  words.some((w) => new RegExp(`\\b${w}\\b`).test(text.toLowerCase()));

export const COLLECTIONS: Record<string, { label: string; blurb: string; match: (p: Product) => boolean }> = {
  colleges: {
    label: "The Residential Colleges",
    blurb: "Fourteen crests. Fourteen loyalties. One courtyard you will defend forever.",
    match: (p) => hasWord(p.name, RESIDENTIAL_COLLEGES),
  },
  varsity: {
    label: "Varsity",
    blurb: "For the rink, the river, the Bowl, and the bleachers.",
    match: (p) => hasWord(p.name, SPORTS),
  },
  family: {
    label: "For the Family",
    blurb: "Proof, in heather gray, that someone at the table got in.",
    match: (p) => hasWord(p.name, FAMILY),
  },
  schools: {
    label: "The Professional Schools",
    blurb: "Law, medicine, art, music, divinity. Advanced degrees, advanced comfort.",
    match: (p) => hasWord(p.name, ["school", "divinity", "law"]),
  },
};
