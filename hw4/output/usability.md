# Campus Customs: Usability Improvements (Problem 9)

Written as we built. Each section says **what we added**, **why it helps** a Campus Customs shopper or the business, and **where to see it** in the running app.

| # | Improvement | Type | Where to see it |
|---|---|---|---|
| 1 | Paw-print wishlist | Front end (+ Dan uses it) | Paw on every product card and product page; paw next to Bag in the menu → Wishlist page |
| 2 | Sorting and filters | Front end | Products page: filter bar above the grid |
| 3 | "Find something similar" for sold-out sizes | Agent / back end | Ask Dan for a sold-out size, e.g. the Brooks Brothers bomber in medium |
| 4 | Fact-checker on Dan's replies | Agent / back end | Green "✓ Checked against the stockroom" badge under Dan's factual replies |

---

## 1. Paw-print wishlist (front end)

**What we added**
- A **paw-print button** in the corner of every product card (catalogue, Dan's Picks, wishlist) and a larger **"Save to Wishlist"** button next to the price on each product page.
- Hovering (or tabbing to it with the keyboard) shows a **"Save to Wishlist"** tooltip. Clicking fills the paw Yale blue ("Saved to Wishlist"), and clicking again removes it. The paw sits outside the card's link, so saving never opens the product by accident.
- A **paw icon with a count next to Bag** in the menu opens the **Wishlist page** ("J.'s wishlist") with the saved items as normal product cards.
- Saved items are stored per account in a new `wishlist_items` table (`backend/wishlist.py`), so they follow the shopper across visits and devices. Guests who tap a paw are taken to log in and brought back to the page they were on.
- **Handsome Dan can read it:** a new `get_my_wishlist` tool lets him see the logged-in shopper's own saved items and suggest similar pieces. Tested: "Based on what I've saved, what else might I like?" → "Since you saved the Yale Dad Hoodie and Saybrook fleece, I think the Saybrook College Crewneck would be a natural next pick…"

**Why it helps**
- *Shoppers:* a no-commitment way to keep track of favorites (gift ideas, "maybe later," comparing colleges) without cluttering the bag.
- *Business:* wishlists signal purchase intent. They make Dan's suggestions more personal (more relevant picks, more items added to bags), and they're the natural basis for future "back in stock" or price-drop reminders. The paw keeps it on-brand with Handsome Dan.

## 2. Sorting and filters on the Products page (front end)

**What we added** (a filter bar above the catalogue grid):
- **Sort:** Featured, Price low → high, Price high → low, Name A → Z.
- **Price:** Any, Under $35, Under $50, Under $75.
- **In my size:** XS-XXL, showing only items in stock in that size.
- **Color:** six swatches (Navy, Gray, Charcoal, Cream, White, Pink) based on each garment's main color.
- **Item type:** Hoodies, Crewnecks, Quarter-zips, Tees, Outerwear, Performance.
- **Hide sold-out items** checkbox.
- A live count ("11 pieces · Navy · in stock in L") and **Clear all filters**. Filters combine and are saved in the page address, so a filtered view can be bookmarked or shared and survives the Back button.

**Why it helps**
- *Shoppers:* 102 products is a lot to scroll. Filters get them to "navy hoodie under $75 in my size" in a few clicks, and the size filter prevents falling for an item that's sold out in their size.
- *Business:* faster discovery means fewer abandoned visits, and fewer "is this in stock in my size?" questions for Dan.
- *Note:* no product is currently sold out in every size, so "Hide sold-out items" changes nothing today. It's ready for when stock runs out. "In my size" is the filter that hides sold-out options today.

**Verified:** Hoodies + Under $75 + Navy + L, sorted by price, gave 11 items, matching a direct database count. The $45 navy UA hoodie was correctly hidden because it's sold out in large.

## 3. "Find something similar" for sold-out sizes (agent / back end)

**What we added**
- A new tool, `find_alternatives(product_id, size)` (`backend/tools.py`), returning an `Alternatives` result (`backend/models.py`):
  - the requested size's real status and count,
  - **adjacent sizes in stock** (one smaller, one larger) of the same item,
  - **up to 4 similar products in stock in the requested size**, ranked by shared college, sport or theme (weighted highest, since loyalty matters most), same garment type, same main color and similar price, each with a short factual "why similar."
- Dan's prompt now says: whenever a size is sold out, call this tool and make the "no" come with a "but." Mention adjacent sizes **neutrally** ("if sizing up works for you"), **never guess how an item fits** (we have no fit data), and offer one or two in-size alternatives as cards.

**Tested** on the Brooks Brothers bomber page, "Do you have this jacket in a medium?":
> "Medium is sold out, I'm afraid. We do have 15 larges if sizing up works for you; in medium, the Divinity School Fleece Sweater or School of Architecture Fleece Sweater are available as navy full-zip alternatives. Woof."

(Small is also sold out, so only the large was offered. Both alternatives really are in stock in medium.)

**Why it helps**
- *Shoppers:* a dead end ("sold out") becomes a next step. Someone who'd happily size up hears that option without being told how something fits.
- *Business:* keeps the sale alive instead of losing the shopper at the sold-out moment, and stays honest (no fit claims we can't back up).

## 4. Fact-checker on Dan's replies (agent / back end)

**What we added**
- `backend/factcheck.py` checks every reply **before it reaches the shopper**:
  - **Prices:** every "$__" must match the catalogue price of a product discussed, or a price a tool returned this turn.
  - **Stock counts:** "15 left," "only 3," "12 in stock" must match a quantity the tools returned.
  - **Sold-out / in-stock claims:** "medium is sold out" or "we have the large" are checked against `inventory` for that product and size (the product named in the sentence, or the product page the shopper is on).
  - **Colors:** colors attributed to a named product must be in its catalogue colors (the color the shopper asked about is allowed, e.g. "closest to pink").
- It runs as a PydanticAI **output validator** in `agent.py`. If anything is wrong, the reply is **not sent**. Dan gets the exact problem ("You said $55, but no product you discussed costs that (real price: $68)") and must fix it, with up to 2 tries. If he still can't, the shopper gets a safe "check the product page for exact numbers" message instead of a wrong one.
- **Visible in the chat:** factual replies carry a small green **"✓ Checked against the stockroom"** badge, or an amber **"✓ Corrected & checked"** if a mistake was caught and fixed. Catches are logged on the server.

**Tested**
- 9 planted test replies: the 4 correct ones passed; the 5 wrong ones (wrong price, wrong stock count, false "sold out," false "in stock," wrong color) were all caught.
- End to end (`backend/factcheck_demo.py`, a stand-in model that lies on purpose): draft "The Basic Hoodie Big Yale is **$55**" was blocked, and Dan's corrected "**$68**" was sent. Corrections: 1.
- Live: Dan's real replies in testing all passed and showed the green badge.

**Why it helps**
- *Shoppers:* they can trust what Dan says about price and stock. The badge makes that trust visible.
- *Business:* AI models occasionally get details wrong. Wrong prices or false "in stock" claims cause angry customers and refund headaches (and potential legal exposure). This turns "we asked the AI to be honest" into "we check it every time." It also costs nothing extra when Dan is right, since the check is plain code, not another AI call.

---

## Bonus improvements (built along the way, beyond the required problems)

| Bonus | What it does | Why it helps |
|---|---|---|
| **Shopping bag** + Under Construction checkout | Logged-in shoppers pick a size, add to bag, change quantities. Checkout is a deliberate "Under Construction" page (no payment data collected). | Makes the site feel like a real store and gives Dan a bag to base suggestions on, safely. |
| **Handsome Dan's Picks** on the page | Browse questions put full product cards at the top of the current page. They collapse to a slim bar when you move on. | Chat results become shoppable without leaving the page. |
| **Recently viewed** strip | The last 8 products viewed, above the footer (browser-only, cleared on log out). | One click back to what you were considering, e.g. after clicking a Dan pick. |
| **"Create a free account" button in the chat** | A guest's first reply includes a sign-up button; their chat is saved to the new account. | Converts guests without making them hunt for a button. |
| **Saved chat history + "Clear my chat history"** | Logged-in chats survive restarts and return visits. Shoppers can delete them anytime. | Continuity for shoppers, with privacy control. |
| **Stronger account security** | 12+ character passwords with mixed characters, 30-minute lockout after 3 failed logins, hashed session tokens. | Protects customer accounts. |
| **Abuse strikes** | Repeated attempts to break Dan's rules end the chat and flag the account for review. | Keeps the assistant safe and on-task. |
| **Dan's honesty and tone tuning** | Short "No, but…" answers, no unasked-for inventory dumps, catalogue colors only, grateful-bulldog reaction for dog items. | Easier to read, more trustworthy, more charming. |
| **J. Peterman catalogue copy** | Every product has an original catalogue-style tagline and story. | A store that feels worthy of the Yale name. |
