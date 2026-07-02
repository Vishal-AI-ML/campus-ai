# Campus-AI Frontend Smoke Test (Playwright)

Ye test **frontend UI** ko auto-check karta hai: har role se login karke uske
saare dashboard pages kholta hai aur dekhta hai koi page toota to nahi
(JS crash / error-boundary / 4xx-5xx / console.error).

Backend wala `e2e_smoke.py` API check karta hai; ye uska frontend jodidaar hai.
Dono milke = **pura project** cover.

## Setup (ek baar)

PowerShell me, frontend folder ke andar:

```powershell
cd E:\campus-ai\frontend
npm i -D @playwright/test
npx playwright install chromium
```

## Chalao

**Live Vercel site ke against (default):**
```powershell
npx playwright test
```

**Local frontend ke against (agar `npm run dev` chal raha ho):**
```powershell
$env:FRONTEND_URL="http://localhost:3000"; $env:API_URL="http://127.0.0.1:8000"
npx playwright test
```

Default:
- `FRONTEND_URL` = https://campus-ai-eta.vercel.app
- `API_URL`      = https://campus-ai-backend-ez7m.onrender.com  (login token ke liye)

## Kya check hota hai

4 role (admin / teacher / tpo / student), har ek ke saare nav pages.
Har page pe:
- HTTP 4xx/5xx
- JS uncaught error (pageerror)
- console.error
- error-boundary text ("Something went wrong" / "Application error" ...)

Ant me summary print hoti hai: kaun se page tute (agar koi).

## Note
- Accounts demo institute ke hain, sabka password `DemoPass123`.
- Token frontend ke `localStorage["campus_ai_token"]` me inject hota hai (UI login
  form pe depend nahi karta - zyada reliable).
