<div>
  <img style="width: 100%" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=header&reversal=true&text=InsightMesh&fontSize=34&fontColor=ffffff&fontAlign=50&fontAlignY=45&animation=twinkling&desc=Ph%C3%A2n%20t%C3%ADch%20t%E1%BB%B1%20nhi%C3%AAn%20ng%C3%B4n%20ng%E1%BB%AF%20c%C3%B3%20ki%E1%BB%83m%20so%C3%A1t%20quy%E1%BB%81n%20ri%C3%AAng%20t%C6%B0%20cho%20PostgreSQL%20%26%20MySQL&descSize=15&descAlign=50&descAlignY=65&color=gradient" />
</div>

<div align="center">
  <a href="README.md">English</a> | <strong>Tiếng Việt</strong>
</div>

<h3 align="center">Đặt câu hỏi tự nhiên. Khám phá dữ liệu an toàn.</h3>

<div align="center">
  <img src="https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI badge" />
  <img src="https://img.shields.io/badge/Frontend-Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js badge" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL badge" />
  <img src="https://img.shields.io/badge/Database-MySQL%208-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL badge" />
  <img src="https://img.shields.io/badge/AI-Gemini%202.5%20Flash-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Gemini badge" />
  <img src="https://img.shields.io/badge/Infra-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker badge" />
</div>

---

## Mục Lục

1. [Tổng Quan Dự Án](#tổng-quan-dự-án)
2. [Kiến Trúc Hệ Thống & Luồng Dữ Liệu](#kiến-trúc-hệ-thống--luồng-dữ-liệu)
3. [Tính Năng Chính](#tính-năng-chính)
4. [Công Nghệ Sử Dụng](#công-nghệ-sử-dụng)
5. [Cấu Trúc Thư Mục](#cấu-trúc-thư-mục)
6. [Hướng Dẫn Khởi Chạy](#hướng-dẫn-khởi-chạy)
7. [Các Endpoint Dịch Vụ](#các-endpoint-dịch-vụ)
8. [Đánh Giá & Quality Gates](#đánh-giá--quality-gates)
9. [Bảo Mật & Quyền Riêng Tư](#bảo-mật--quyền-riêng-tư)
10. [Giới Hạn Đã Biết](#giới-hạn-đã-biết)
11. [Xử Lý Sự Cố](#xử-lý-sự-cố)

---

## Tổng Quan Dự Án

InsightMesh là workspace phân tích dữ liệu bằng ngôn ngữ tự nhiên, ưu tiên chạy local, dành cho PostgreSQL và MySQL. User có thể kết nối datasource read-only, xem schema và relationship map, đặt câu hỏi, kiểm tra SQL và execution trace, sau đó lưu verified result thành analysis hoặc dashboard widget.

MongoDB được chủ động đưa ra ngoài phạm vi V1. Provider enrichment là tùy chọn: introspection, profiling, semantic retrieval, kiểm tra SQL và thực thi deterministic vẫn có thể hoạt động mà không cần AI provider bên ngoài.

### Vấn Đề → Giải Pháp → Kết Quả (PSR)

| Khía cạnh | Mô tả |
|---|---|
| **Vấn đề** | Câu hỏi nghiệp vụ dùng ngôn ngữ tự nhiên, trong khi database thể hiện bằng schema kỹ thuật. Analyst cần cách an toàn để hiểu bảng, sinh SQL, xác thực kết quả và tái sử dụng analysis mà không gửi dữ liệu thô cho LLM. |
| **Giải pháp** | Xây semantic layer có kiểm soát quyền riêng tư từ metadata và profile, truy xuất schema context liên quan, sinh SQL theo dialect, kiểm tra bằng SQLGlot, thực thi qua connector read-only và hiển thị result có thể truy vết. |
| **Kết quả** | Quy trình Ask có thể tái lập cho PostgreSQL và MySQL, gồm inspect datasource, ERD, suggestions, chart/table fallback, dashboard, saved analysis, query history, retention và deterministic evaluation. |

### Kết quả release đã đo lường

Bộ đánh giá hybrid mới nhất có 37 case (25 PostgreSQL và 12 MySQL, tạo ngày 2026-09-21):

| Chỉ số | Kết quả |
|---|---:|
| Status accuracy | 100% |
| Execution rate | 100% |
| Result accuracy | 100% |
| Mean entity recall | 100% |
| Mean entity precision | 66.98% |
| Join-path accuracy | 100% |
| Result accuracy easy / medium / hard | 100% / 100% / 100% |

Bộ test có thêm 2 case ambiguous, 3 case out-of-scope và 5 case unsafe; mọi terminal status đều được phân loại đúng.

---

## Kiến Trúc Hệ Thống & Luồng Dữ Liệu

Ranh giới hệ thống, ranh giới quyền riêng tư của provider, query path deterministic và sự tách biệt datasource nằm trong [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

~~~mermaid
flowchart LR
    U[User] --> F[Next.js Ask workspace]
    F --> A[FastAPI API]
    A --> M[(Metadata DB - PostgreSQL + pgvector)]
    A --> S[Semantic retrieval - chỉ metadata]
    S --> L[LLM / embedding provider - tùy chọn]
    A --> V[SQLGlot validator - read-only policy]
    V --> C[Dialect connector]
    C --> PG[(PostgreSQL source)]
    C --> MY[(MySQL source)]
    A --> R[Verified result, trace, dashboard]
    R --> F
~~~

### Luồng runtime

1. **Onboard** — xác thực credential, discover schema metadata, profile thống kê an toàn và xây semantic index có giới hạn quyền riêng tư.
2. **Understand** — hiển thị entity, field, sample row an toàn, profile, relationship, ERD layout và ba question suggestion theo datasource.
3. **Ask** — phân loại câu hỏi, truy xuất metadata liên quan, sinh SQL theo dialect, kiểm tra safety và thực thi qua connector.
4. **Verify** — kiểm tra shape/value, chọn table/chart/KPI phù hợp và hiển thị SQL cùng structured trace an toàn.
5. **Reuse** — lưu analysis, lưu dashboard widget, refresh result ngay trên saved item hoặc rerun thành recent activity mới.

### Hình ảnh minh họa

<div align="center">
  <img src="docs/assets/screenshots/ask-desktop.png" alt="InsightMesh Ask workspace" width="49%" />
  <img src="docs/assets/screenshots/dashboard-mobile.png" alt="InsightMesh dashboard trên mobile" width="49%" />
</div>
<div align="center">
  <img src="docs/assets/screenshots/source-detail-desktop.png" alt="InsightMesh datasource detail và ERD" width="80%" />
</div>

Video demo trình duyệt nằm tại [docs/assets/recordings/insightmesh-ask-demo.webm](docs/assets/recordings/insightmesh-ask-demo.webm). Có thể chạy browser coverage bằng test profile command trong phần dưới.

---

## Tính Năng Chính

### 1. Onboarding datasource read-only

Kết nối PostgreSQL hoặc MySQL bằng credential được mã hóa, allowlist database, kiểm tra connectivity và refresh metadata mà không lưu raw row hoặc secret trong API response.

### 2. Inspect datasource và ERD

Xem entity, field, sample row an toàn, semantic profile và relationship. ERD hỗ trợ kéo thả, reset layout và tự highlight entity liên quan khi chọn một entity. Sources và Ask inspect mode dùng chung interaction model.

### 3. Question suggestion theo datasource

Ask workspace hiển thị ba suggestion inline từ context datasource đang active.

### 4. Query ngôn ngữ tự nhiên theo dialect

Runtime chọn PostgreSQL hoặc MySQL deterministic, sinh SQL có giới hạn, kiểm tra bằng SQLGlot, chặn thao tác nguy hiểm, thực thi read-only và hỗ trợ bounded repair cho lỗi đủ điều kiện.

### 5. Verified result và visualization

Kết quả gồm status trung thực, bảng phân trang, SQL, trace an toàn, warning, đề xuất chart/KPI và table fallback khi result không phù hợp để vẽ.

### 6. Analysis và dashboard có thể tái sử dụng

Lưu analysis đã validate cùng query definition và result snapshot, refresh saved result tại chỗ và lưu result phù hợp thành dashboard widget. Recent activity là lịch sử thực thi; saved analysis là tài sản dùng lại lâu dài.

### 7. History có retention

Query artifact gần đây mặc định hết hạn sau 7 ngày và run summary sau 90 ngày. Saved analysis sao chép query definition đã validate nên không bị cleanup của recent activity xóa.

---

## Công Nghệ Sử Dụng

* **FastAPI + Python** — typed API, state machine deterministic, SQLGlot validation, connector, result verification và evaluation.
* **PostgreSQL 16 + pgvector** — metadata ứng dụng, semantic artifact, embedding, query run, saved analysis, dashboard và widget.
* **Next.js + React + TypeScript + Tailwind CSS** — workspace Sources, Ask, History và Dashboard responsive.
* **PostgreSQL và MySQL 8** — source engine được hỗ trợ với thực thi read-only.
* **Gemini 2.5 Flash** — provider structured-generation chính; OpenRouter là fallback có giới hạn nếu được cấu hình.
* **Docker Compose + Alembic + uv + npm ci** — service tái lập, migration và dependency có lock.
* **Playwright + Vitest** — browser acceptance và component/unit coverage.

---

## Cấu Trúc Thư Mục

~~~text
insightmesh-multi-source-analytics/
├── compose.yaml                         # Ứng dụng local và demo database
├── .env.example                         # Template biến môi trường
├── README.md / README_VI.md             # Tài liệu song ngữ
├── backend/                             # FastAPI, connector, query, semantic, service
├── frontend/                            # Next.js route, component, test, e2e
├── demo/postgres/                       # PostgreSQL demo store
├── demo/mysql/                          # MySQL demo store
├── docs/                                # Plan, PRD, design, architecture, evidence
├── design-system/insightmesh/           # Visual system đã phê duyệt
└── tests/                               # Backend và foundation test suite
~~~

---

## Hướng Dẫn Khởi Chạy

### Yêu Cầu

* Docker Desktop với Linux containers, hoặc Docker Engine với Compose v2+.
* Git nếu cần clone repository.
* Không cần cài Python hoặc Node.js trên host.

### Bước 1: Khởi tạo môi trường

~~~powershell
cd D:\project\insightmesh-multi-source-analytics
Copy-Item .env.example .env
docker compose config --quiet
~~~

Giá trị mặc định chạy được mà không cần sửa environment file. Chỉ dùng giá trị development và không commit secret thật. Credential khởi tạo database chỉ áp dụng khi volume tạo lần đầu; đổi environment file không tự đổi password hiện có.

### Bước 2: Khởi chạy stack

~~~powershell
docker compose up --build -d --wait --wait-timeout 240
docker compose ps
~~~

Bốn service chạy lâu dài cần healthy; migration service thoát code 0 là đúng. Muốn bật MySQL:

~~~powershell
docker compose --profile mysql up --build -d --wait --wait-timeout 240
~~~

### Bước 3: Kết nối và hỏi

Mở Sources, chọn PostgreSQL hoặc MySQL, nhập account read-only, host/port/database và nhấn **Test connection**. Với database trong Compose dùng service host demo-postgres hoặc demo-mysql; localhost là database publish ra host, không phải container bên cạnh.

Activate datasource, inspect schema hoặc chọn suggestion, đặt câu hỏi rồi kiểm tra verified result. **Refresh** cập nhật saved analysis tại chỗ; **Run again** cố ý tạo execution mới trong recent activity.

### Bước 4: Chạy quality gates

~~~powershell
docker compose exec backend python tests/foundation_smoke.py
docker compose run --rm backend uv run pytest
docker compose run --rm backend uv run ruff check .
docker compose run --rm backend uv run mypy .
docker compose run --rm --no-deps frontend npm run lint
docker compose run --rm --no-deps frontend npm run typecheck
docker compose run --rm --no-deps frontend npm run test
docker compose run --rm --no-deps frontend npm run build
docker compose --profile test run --rm e2e
~~~

---

## Các Endpoint Dịch Vụ

| Service | URL | Mục đích |
|---|---|---|
| **Frontend** | [http://localhost:3000](http://localhost:3000) | Sources, Ask, History và Dashboards |
| **Backend health** | [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) | Liveness/readiness API |
| **API docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Tài liệu OpenAPI |
| **Frontend-to-backend health** | [http://localhost:3000/api/health](http://localhost:3000/api/health) | Kiểm tra kết nối từ browser |

Metadata database và demo database là service nội bộ của Compose, mặc định không bind port ra host.

### Credential demo datasource

| Source | Host trong Compose | Port | Database | User | Password |
|---|---|---:|---|---|---|
| PostgreSQL demo | demo-postgres | 5432 | insightmesh_demo | demo_reader | DEMO_READER_PASSWORD |
| MySQL demo | demo-mysql | 3306 | insightmesh_demo | demo_reader | DEMO_READER_PASSWORD |

Cả hai account demo chỉ có quyền SELECT. Với database cài trực tiếp trên host, dùng địa chỉ backend truy cập được và account database thật.

---

## Đánh Giá & Quality Gates

~~~powershell
docker compose --profile mysql up -d demo-mysql
docker compose exec backend python -m evals.run_combined_evaluation --strategy hybrid
~~~

Command ghi report theo datasource và difficulty cùng combined-latest.json. Release suite bao phủ easy, medium, hard, ambiguous, out-of-scope và unsafe questions.

---

## Bảo Mật & Quyền Riêng Tư

* Password datasource được mã hóa khi lưu và không trả về bởi API.
* Connector bắt buộc read-only; SQLGlot chặn write operation và multi-statement.
* Context gửi provider chỉ gồm metadata, profile và schema liên quan. Raw row, credential, prompt, embedding và hidden reasoning bị loại khỏi payload.
* Query trace có cấu trúc, có thể inspect mà không làm lộ execution internals nhạy cảm.
* Query artifact gần đây có retention; saved analysis giữ query definition đã validate và result snapshot.
* Giá trị Compose chỉ dành cho development. Production cần role runtime/migration riêng, secret manager, image digest cố định và TLS.

---

## Giới Hạn Đã Biết

* MongoDB nằm ngoài phạm vi V1.
* Query-run creation là synchronous; UI hiển thị trạng thái chờ trung thực.
* Dashboard arrangement hiện dùng control move có thể thao tác bằng bàn phím.
* Retrieval-context caching được hoãn cho đến khi có bằng chứng về repeat-hit và tiết kiệm chi phí.
* Base-image chưa được pin bằng digest.
* Semantic enrichment qua provider cần API key; introspection local và deterministic test vẫn chạy được khi thiếu provider.

---

## Xử Lý Sự Cố

* **Kết nối thất bại từ browser** — localhost trỏ tới backend container. Dùng demo-mysql, demo-postgres, host.docker.internal cho service trên host qua Docker Desktop, hoặc LAN address có thể truy cập.
* **Không discover được entity** — kiểm tra database đã allowlist, quyền đọc information_schema, schema có table và nhấn **Refresh metadata**.
* **Kết nối được nhưng result out-of-scope** — hỏi về field trong datasource active và thử suggestion được sinh tự động.
* **Chart thành table** — result có thể thiếu categorical dimension và numeric measure; table là fallback trung thực.
* **Không có MySQL demo** — bật MySQL profile và kiểm tra health.
* **Migration cũ** — chạy migration service và xem logs.

Tài liệu liên quan: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/InsightMesh_PRD.md](docs/InsightMesh_PRD.md), [docs/TECHNICAL_DESIGN.md](docs/TECHNICAL_DESIGN.md) và [design-system/insightmesh/MASTER.md](design-system/insightmesh/MASTER.md).

<div>
  <img style="width: 100%" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer&reversal=true&text=H%E1%BB%8Fi%20r%C3%B5%20%E2%80%A2%20Ki%E1%BB%83m%20tra%20an%20to%C3%A0n%20%E2%80%A2%20T%C3%A1i%20s%E1%BB%AD%20d%E1%BB%A5ng%20t%E1%BB%B1%20tin&fontSize=22&fontColor=ffffff&fontAlign=50&fontAlignY=50&animation=twinkling&color=gradient" />
</div>
