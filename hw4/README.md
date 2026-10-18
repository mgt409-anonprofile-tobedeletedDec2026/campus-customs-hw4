# Campus Customs: Yale apparel shop with Handsome Dan, an AI shopping assistant

Course homework project (MGT 409, AI Foundations for Managers, Homework 4). It's a React + Vite + TypeScript storefront with a FastAPI backend, and the chat assistant is a **PydanticAI agent** that answers only from the store's database. Not affiliated with any real retailer.

**What's inside:** product catalogue with filters, single-item pages, accounts with secure passwords, a shopping bag, a paw-print wishlist, recently viewed items, and **Handsome Dan**, a chat assistant who:
- looks up prices and stock with tools,
- puts matching product cards on the page,
- remembers logged-in shoppers,
- suggests alternatives when a size is sold out,
- has every answer fact-checked against the database before it's sent.

## Where to look

| Path | What it is |
|---|---|
| `AI_prompts.md` | Every prompt given to the AI coding assistant, problem by problem |
| `backend/main.py` | FastAPI app: products, accounts, bag, wishlist, and the `/api/chat` route |
| `backend/agent.py`, `backend/tools.py`, `backend/models.py`, `backend/prompts/prompt.md` | The agent: wiring and loop guards, read-only tools, structured types, and instructions with safety rules |
| `backend/*.py` (other) | Accounts (`auth.py`), bag (`cart.py`), wishlist, chat history, fact-checker, audit trail, spam limits, privacy scrubbing |
| `frontend/` | The storefront (React + Vite + TypeScript) |
| `output/harness.md` | How the whole system works: data, tools, models, safety, specs |
| `output/usability.md`, `output/design.md` | Problem 9 and 10 write-ups |
| `output/app_check.html` | Test report with screenshots (double-click to open) |
| `output/audit_trail.json` | Append-only log of the agent's tool use and stop reasons (no personal data) |

## How to run it

You'll need **Python 3.12+**, **Node.js 20+**, and an API key for the AI model (a Portkey key, as used in the course).

### 1. Add the data pack (not in this repository)

Unzip the course `data.zip` so these sit inside this `hw4` folder:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/        (product images referenced by the catalogue)
```

The app adds its own tables (logins, bags, wishlists) to this database the first time it starts.

### 2. Create your `.env`

Copy `.env.example` to a new file named `.env` in this `hw4` folder and fill in your key:

```
PORTKEY_API_KEY=your-key-here
OPENAI_MODEL=gpt-5.6-luna
```

`.env` is git-ignored. Never commit it.

### 3. Install everything (one time)

From the `hw4` folder:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd frontend
npm install
```

(On macOS/Linux use `.venv/bin/pip` instead of `.venv\Scripts\pip`.)

### 4. Start the back end

From `hw4/backend`, with the virtual environment active (`..\.venv\Scripts\activate` on Windows, `source ../.venv/bin/activate` on macOS/Linux):

```
uvicorn main:app --reload --port 8000
```

### 5. Start the website

In a second terminal, from `hw4/frontend`:

```
npm run dev
```

Then open **http://localhost:5173**. The website forwards `/api` and `/images` requests to the back end on port 8000.

**Windows shortcut:** after steps 1-3, double-click `start_site.bat` to start both and open the browser. Close the two windows it opens to stop.

### Try it

- Log in with the course's seeded test account (`test@campuscustoms.yale.edu` / `password`), or create an account (new passwords need 12+ characters with upper and lower case, a number and a symbol).
- Open the chat (Handsome Dan, bottom right) and ask: *"What hoodies do you have?"*, *"Do you have the Brooks Brothers bomber in a medium?"*, or, on a product page, *"Do you have this in pink?"*

### Demos that don't call the AI

From `hw4/backend`: `python factcheck_demo.py` (the fact-checker catching and correcting a wrong price) and `python loopguard_demo.py` (the loop guards stopping a stuck agent).

## Notes

- **Model:** `OPENAI_MODEL` (default `gpt-5.6-luna`) via Portkey, configured in one place (`backend/agent.py`). Loop limits, caps and safety rules are documented in `output/harness.md`.
- **Style:** the course workspace's default app style is black and pink. This project deliberately uses Yale blue and white instead, because the assignment asked us to match the Campus Customs storefront's style. Pink appears only in the test report's Elle Woods theme.
- **Artwork:** the engraved skyline was generated in ChatGPT from a written prompt (logged in `AI_prompts.md`, Problem 10). Product catalogue copy was written for this project.
- **Privacy:** no real customer data is included. Screenshots use a fictional test account.
