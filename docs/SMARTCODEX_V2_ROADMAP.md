# SmartCodex v2 — Roadmap Implementasi Intelligent Task Orchestrator

**Status:** Rencana implementasi. **Profil awal: TESTING / LOW-COST**; fitur v2 belum tersedia.
**Tanggal penyusunan:** 14 Oktober 2026
**Target lingkungan:** Windows / PowerShell, Python 3, Codex CLI, login ChatGPT Plus.
**Repo pengembangan:** `D:\atsal\AI-Orchestrator`
**Instalasi launcher saat ini:** `C:\tools\smartcodex\smartcodex.py`

## A. Tujuan produk

SmartCodex adalah CLI yang menerima sebuah tugas coding, memahami konteks repository secukupnya, lalu:

1. Untuk pekerjaan kecil, langsung memilih model murah dan menjalankan **satu** Codex task tanpa planning/delegasi mahal.
2. Untuk pekerjaan besar, menyusun rencana subtugas terstruktur, menilai kompleksitas/risiko/dependensi, memilih model serta reasoning per subtugas, dan mengeksekusinya dalam urutan yang aman.
3. Menjalankan validasi, menahan tindakan berisiko tanpa izin, dan mengeskalasi hanya pada subtugas yang benar-benar memerlukan kemampuan lebih tinggi.
4. Menyimpan state supaya bisa melihat, menghentikan, dan melanjutkan pekerjaan; mencatat penggunaan token dari router, planner, executor, serta verifier jika metriknya tersedia.
5. Tetap menggunakan autentikasi Codex yang didukung oleh akun ChatGPT Plus. Tidak mewajibkan OpenRouter, LiteLLM, atau OpenAI API key.

**Bukan tujuan awal:** mendukung seluruh IDE, menjalankan banyak penulis kode paralel, mengotomatiskan deployment/production, atau menjamin penghematan persentase tertentu.

## B. Yang sudah berfungsi (baseline v1)

- Perintah `smartcodex` dari PowerShell, router berbasis aturan dan classifier AI.
- `codex exec` memakai model serta reasoning hasil pilihan router.
- Luna Low berhasil untuk merangkum README; Sol Medium berhasil untuk audit konfigurasi.
- `AGENTS.md`, `.codex/config.toml`, dan `fast_worker`/`standard_worker`/`deep_worker` sudah disiapkan.
- Satu uji delegasi memperlihatkan aktivitas kolaborasi tetapi belum membuktikan model subagent melalui trace.
- Pemilihan model sekarang baru per **prompt awal**; bukan per subtugas dan belum menganalisis isi repository sebelum routing.

## C. Prinsip penghematan dan keamanan (non-negotiable)

1. **Simple task → direct execution.** Jangan memanggil planner/subagent jika tugas kecil sudah jelas.
2. **Prompt panjang ≠ tugas berat.** Nilai risiko, dependensi, ketidakpastian, scope edit, dan kebutuhan reasoning.
3. **Read minimum needed.** Awali dengan metadata git, file tree terbatas, manifests, dan file relevan; hindari `vendor/`, `node_modules/`, `.git/`, build artifacts, dan `.env`.
4. **Plan only when useful.** Task decomposition bukan kewajiban untuk setiap prompt.
5. **Sequential write by default.** Jalankan penulisan kode satu per satu; paralelisme hanya untuk pemeriksaan read-only independen pada fase lanjut.
6. **Never silently escalate.** Catat alasan perpindahan model; batasi eskalasi standar maksimal satu kali per subtugas, kecuali disetujui pengguna.
7. **Never silently mutate risky state.** Tidak boleh `git push`, deploy, destructive DB migration, penghapusan massal, atau baca/ekspos secret tanpa persetujuan eksplisit.
8. **Track total workload.** Sertakan token klasifikasi, planning, task workers, verifikasi, dan retry, bukan hanya model pelaksana.
9. **No claims without test.** Jangan menyebut sukses bila tes belum dijalankan; jangan mengaku model tertentu bekerja tanpa trace yang memadai.
10. **Treat model availability as runtime data.** Cek model/effort yang tersedia, fallback transparan, jangan berasumsi Astra aktif pada akun.

## C1. Kebijakan model selama pengembangan — TESTING / LOW-COST

**Mulai 14 Oktober 2026, seluruh tahap pengembangan SmartCodex v2 memakai profil testing murah.** Tujuan tahap ini membuktikan orkestrasi dan keamanan, belum memaksimalkan kemampuan model.

| Kategori logis | Model | Reasoning | Perilaku |
| --- | --- | --- | --- |
| `simple` | `gpt-6-luna` | `low` | Tugas terlokalisasi; satu eksekusi langsung |
| `standard` | `gpt-6-luna` | `medium` | Pekerjaan normal tanpa model premium |
| `deep` | `gpt-6-luna` | `high` | Pekerjaan sulit saat masih eksperimen |
| `fallback` | `gpt-6.1-sol` | `low` | Hanya setelah bukti ketidakmampuan Luna **dan persetujuan pengguna** |
| `premium` | **Nonaktif** | — | Astra / Sol High tidak dipakai selama testing |

Classifier: `gpt-6-luna` `low` hanya jika heuristik tidak cukup. Planner: `gpt-6-luna` `medium` dan **hanya** untuk tugas gabungan. Verifikasi utamakan unit test/linter lokal yang tidak membutuhkan token AI.

**Kendali kuota:** maksimal 1 writer; jangan memecah tugas kecil; batasi planner secara default hingga 5 subtugas (dapat diubah); tidak ada retry model otomatis atau eskalasi model lebih mahal tanpa persetujuan; catat total token classifier + planner + worker + verifier + retries. Jika tes menemui tugas yang terlalu sulit, boleh tandai `blocked` alih-alih memaksakan model mahal. Kualitas kode dan keamanan tidak boleh dikorbankan diam-diam.

**Pemisahan konfigurasi:** simpan mapping dalam `config/model_profiles.toml` dengan profil `testing` dan `production`. Kode router dan agent memakai *kategori logis* `simple/standard/deep/fallback`, bukan model ID yang di-hardcode. Contoh konfigurasi ada di file pendamping `SMARTCODEX_MODEL_PROFILES.toml` (template v2; belum dibaca oleh launcher v1).

**Jangan merusak v1:** `--force-tier sol-low` pada launcher lama harus tetap berarti Sol Low; jangan diam-diam memetakannya ke Luna. Saat Tahap 01–03, tambahkan sistem profil **baru** dengan kompatibilitas CLI lama. Jika ingin memakai v1 sebelum tahap itu selesai, gunakan `--force-tier luna-low` untuk pengujian sederhana; untuk Luna Medium/High bisa menjalankan Codex langsung dengan override model/reasoning.

**Pembuktian multi-model di Tahap 05:** perbedaan Luna Low/Medium/High membuktikan routing **reasoning per subtugas**, bukan pergantian *model ID*. Tambahkan satu tes kecil dan terkontrol menggunakan fallback Sol Low dengan persetujuan untuk membuktikan pergantian model ID. Jangan menjalankan eksperimen mahal berulang hanya untuk memenuhi metrik.

**Setelah stabil:** evaluasi pekerjaan yang *sama* pada `testing` dan `production`, termasuk hasil tes, retry, total token, durasi, dan jatah penggunaan. Aktifkan model yang lebih kuat hanya apabila manfaatnya terbukti dan kamu setujui.

## D. Arsitektur target

```text
User / CLI
  |
  v
Command Parser & Repo Guard
  |
  v
Scope Analyzer (lokal, murah) --> Simple? --> Direct Codex task (profil testing: Luna Low)
  |
  v
AI Task Planner (read-only, JSON terstruktur)
  |
  v
Plan Validator (schema, dependencies, paths, safety)
  |
  v
Model Router --> Task DAG / Scheduler --> Codex Runner per subtugas
                                              |
                                              v
                                      Targeted tests / verifier
                                              |
                                   pass ------+------ fail
                                    |                  |
                                    v                  v
                              Integrate result  One bounded escalation
                                    |                  |
                                    +------------------+
                                              |
                                              v
                                       State + Telemetry
```

Komponen utama:
- `RepoAnalyzer`: konteks file relevan, branch, working-tree status, manifests dan petunjuk arsitektur.
- `Classifier`: klasifikasi awal dengan heuristic atau model murah saat ambigu.
- `Planner`: daftar subtugas dengan ID, tujuan, `depends_on`, scope files, risiko, verifikasi, dan rekomendasi tier.
- `PlanValidator`: skema JSON, DAG tidak siklik, path tetap di workspace, tanpa tugas implisit berbahaya.
- `Router`: tabel tier dan override reasoning; periksa ketersediaan model.
- `Scheduler`: single-writer default, checkpoint setelah tiap subtugas, file overlap detection.
- `CodexRunner`: `codex exec --json` dengan argument list aman, sandbox yang sesuai, baca event terstruktur.
- `Verifier`: perintah test yang memang terdeteksi/didefinisikan; tidak selalu menjalankan full test suite.
- `SessionStore`: progress di direktori lokal yang di-ignore Git, bukan disimpan di prompt terus-menerus.
- `UsageTracker`: pemakaian per tahap, model, retries, durasi, tanda sukses/fail.

## E. Struktur repository yang disarankan

```text
AI-Orchestrator/
├── README.md
├── pyproject.toml
├── config/
│   └── model_profiles.toml  # testing/production; ditambahkan saat tahap konfigurasi
├── src/
│   └── smartcodex/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── repo_analyzer.py
│       ├── classifier.py
│       ├── planner.py
│       ├── plan_schema.py
│       ├── router.py
│       ├── scheduler.py
│       ├── codex_runner.py
│       ├── verifier.py
│       ├── state_store.py
│       ├── usage.py
│       └── security.py
├── prompts/
│   ├── classify.md
│   ├── plan.md
│   └── execute.md
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── examples/
│   ├── task-simple.md
│   └── task-large.md
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   └── evaluation.md
└── templates/
    ├── AGENTS.md
    └── codex-agents/
```

Konfigurasi pribadi `AGENTS.md` dan `.codex/` boleh tetap lokal. Saat launcher dibangun dalam repository ini, simpan versi template yang bisa dibagikan di `templates/`, bukan mencampur setting personal dengan kode program. Pada proyek target, simpan `.smartcodex/` untuk state/log lokal yang di-ignore Git.

## F. Tahapan pengerjaan dan Definition of Done

### Tahap 00 — Snapshot & baseline (wajib)
- Simpan salinan v1; pastikan git clean/branch eksperimen; catat `codex --version`, Python, jenis login, CLI flags, dan model yang bisa dijalankan.
- Siapkan 6–10 contoh tugas: typo UI, baca file, tambah validasi, refactor biasa, debugging lintas modul, implementasi fitur besar.
- Jalankan baseline secara terkendali pada beberapa tugas read-only dan simpan model, exit code, time, token jika tersedia, hasil verifikasi.
- **Lulus:** v1 tidak rusak; baseline tersimpan, tanpa file production diubah.

### Tahap 01 — Pindahkan launcher ke source repo
- Migrasikan `smartcodex.py` ke package Python, tanpa mengganti perilaku yang sudah lolos.
- Tambahkan `pyproject.toml` + entry point `smartcodex`; konfigurasi personal dapat menunjuk instalasi repo.
- Unit test parser argumen, route rules, tier overrides, fallback, dan penggunaan subprocess tanpa shell injection.
- **Lulus:** `smartcodex --help`, `--dry-run`, `--router ai`, dan mode exec tetap berfungsi sesuai v1.

### Tahap 02 — Project-aware scope analyzer (lokal)
- Dapatkan root Git, branch, file dirty, tracked file tree, bahasa/framework dari manifest (`composer.json`, `package.json`, dll.).
- Cari path relevan berdasarkan prompt tanpa membaca seluruh isi repo.
- Abaikan secrets dan direktori besar; batasi jumlah file/bytes/tokens yang dikirim ke classifier.
- Mode read-only default; jika repo bukan Git, gunakan batasan path aman yang setara.
- **Lulus:** dari fixture Laravel dan JS, analyzer mengembalikan ringkasan ringkas yang relevan, tidak pernah memuat `.env`.

### Tahap 03 — Intent gate: Direct vs Plan
- Tentukan kapan satu pekerjaan cukup langsung dikerjakan vs perlu decomposition.
- Jika jelas sederhana: local heuristic -> `simple` -> Luna Low pada profil testing -> satu run.
- Jika tidak jelas: classifier murah dengan ringkasan konteks repo terbatas.
- Tambahkan alasan pilihan; confidence rendah harus tercatat, bukan disembunyikan. Gunakan profil `testing` sebagai default baru setelah kompatibilitas v1 terjamin.
- **Lulus:** tugas typo tidak memanggil planner, tugas fitur lintas modul masuk mode plan, panjang teks tidak menjadi satu-satunya faktor.

### Tahap 04 — Task planner + schema
- Hasilkan rencana JSON terstruktur, misalnya `tasks: [{id, title, goal, depends_on, files, risk, tier, effort, verification, acceptance}]`.
- Pakai output schema untuk menghindari parsing teks bebas; simpan user prompt terpisah dari instruksi sistem.
- Validasi DAG, jumlah task (misalnya 2–8 default), file scope, risiko, kualitas acceptance criteria.
- `smartcodex plan --file task.md` menampilkan rencana tanpa perubahan kode.
- **Lulus:** output selalu valid atau gagal aman; dependency order jelas; tidak menjalankan write saat plan-only.

### Tahap 05 — Scheduler + per-task model execution (MVP inti)
- Implementasi topological scheduler, satu writer, checkpoint per subtugas.
- Set model dan reasoning pada setiap pemanggilan `codex exec` melalui profil terpilih (default `testing`), bukan nilai yang di-hardcode.
- Worker menerima hanya tujuan dan konteks relevan serta ringkasan temuan sebelumnya, bukan semua histori agent.
- Deteksi scope overlap dan file yang berubah di luar rencana; berhenti jika melanggar batas.
- **Lulus:** satu prompt besar menjalankan minimal dua subtugas dengan pasangan (model, effort) berbeda dan log yang membuktikannya; tes tambahan model ID berbeda dijalankan sekali secara terbatas dengan persetujuan.

### Tahap 06 — Validation + selective escalation
- Identifikasi test commands yang relevan dari repo atau konfigurasi; mulai dari test fokus.
- Jika gagal, klasifikasi penyebab: kesalahan kode, missing environment, dependency, atau tool restriction.
- Eskalasi satu tingkat hanya untuk masalah yang benar-benar memerlukan reasoning lebih kuat, bukan karena tool gagal install.
- Pada profil `testing`, tidak ada eskalasi model otomatis; fallback Sol Low perlu persetujuan eksplisit. Setelah stabil, profil `production` boleh menerapkan maksimum satu eskalasi per subtugas; Astra tetap opt-in.
- **Lulus:** tes gagal memicu tindakan yang tepat; kegagalan lingkungan tidak menyebabkan retry model mahal tanpa alasan.

### Tahap 07 — State persistence, status, resume
- Persist task state: `planned`, `running`, `passed`, `failed`, `blocked`, `skipped`; simpan hash/signature rencana, perubahan Git, model, dan checkpoint.
- Perintah `smartcodex status`, `smartcodex resume`, `smartcodex cancel`.
- Saat resume, cek perubahan Git/working tree; jangan menjalankan task completed dua kali tanpa alasan.
- **Lulus:** hentikan setelah subtugas pertama, lanjutkan secara aman tanpa mengulang perubahan pertama.

### Tahap 08 — Usage telemetry & budget guard
- Tangkap event `codex exec --json` (token jika muncul, sesi, command outcomes, model, waktu); hitung classifier + planner + workers + verifier.
- Bedakan `reported_tokens` dan `unknown_tokens` bila event tidak cukup detail.
- `smartcodex usage --last` dan laporan per-task.
- Soft budget: warning; hard stop pada batas yang dapat didukung, tanpa mengklaim bisa mengontrol kuota Plus server-side secara eksak.
- **Lulus:** laporan total dan rincian tiap tahap bisa direproduksi dari trace tanpa mengekspose prompt/secret ke log.

### Tahap 09 — Persistent turn routing melalui Codex App Server (lanjutan)
- Bangun adapter untuk `thread/start`, `thread/resume`, `turn/start`, streaming events dan approval.
- Pakai override `model` + `effort` per giliran sambil memakai thread yang sama, jika didukung oleh versi CLI dan akses akun.
- Tidak mengganti model tengah giliran aktif; perubahan diterapkan pada giliran berikutnya atau subtugas baru.
- Bedakan thread user conversation vs task execution ledger untuk menghindari konteks berlebihan.
- **Lulus:** dua prompt berurutan yang saling berhubungan dapat memakai model berbeda dan tetap memahami state sebelumnya.

### Tahap 10 — Reliability, docs, eval & release
- Jalankan tugas yang sama menggunakan baseline satu model dan v2 routing, pada repo fixture/snapshot yang dapat di-reset.
- Bandingkan keberhasilan, kualitas, regresi, token total, latensi, dan jumlah retry; jangan bandingkan dua tugas berbeda.
- Audit izin read-only vs write, secret handling, prompt injection dari repository, git dirty guards, interruption handling.
- Siapkan README, install Windows, troubleshooting, changelog, versioning, release ZIP/installer.
- **Lulus:** semua gate keamanan, smoke test, integration test, recovery test, dan eval set terpenuhi.

## G. Perintah CLI yang ditargetkan

> Semuanya contoh **interface yang akan dibuat**, belum otomatis didukung oleh launcher v1.

```powershell
# Routing langsung untuk tugas kecil
smartcodex "Ubah teks tombol Simpan menjadi Kirim"

# Preview rencana, tanpa write
smartcodex plan --profile testing --file .\task.md

# Eksekusi setelah melihat plan, dengan konfirmasi perubahan
smartcodex run --profile testing --file .\task.md

# Pantau kerja yang sudah dimulai
smartcodex status

# Lanjutkan pekerjaan yang terhenti
smartcodex resume

# Lihat rincian penggunaan model dan token
smartcodex usage --last

# Kendali manual bila benar-benar diperlukan
smartcodex run --profile testing --file .\task.md --max-tier sol-high
```

## H. Contoh output planner

```json
{
  "task_id": "campaign-feature-001",
  "requires_plan": true,
  "tasks": [
    {
      "id": "T1",
      "title": "Inspect current campaign patterns",
      "depends_on": [],
      "tier": "simple",
      "risk": "low",
      "files": ["routes/web.php", "app/Http/Controllers"],
      "verification": "Report exact findings and files"
    },
    {
      "id": "T2",
      "title": "Implement targeted validation",
      "depends_on": ["T1"],
      "tier": "standard",
      "risk": "medium",
      "files": ["app/Http/Controllers"],
      "verification": "Run targeted feature tests"
    },
    {
      "id": "T3",
      "title": "Verify integration edge cases",
      "depends_on": ["T2"],
      "tier": "deep",
      "risk": "medium",
      "files": ["tests"],
      "verification": "Test edge cases and explain failures"
    }
  ]
}
```

Contoh model adalah usulan per pekerjaan, bukan keputusan yang harus selalu sama. Planner wajib punya schema yang divalidasi sebelum dieksekusi.

## I. Test suite yang wajib ada sebelum penggunaan rutin

| Test | Harapan |
| --- | --- |
| Typo label sederhana | Satu run Luna Low; tidak memanggil planner/subagents |
| Prompt panjang tetapi tugas sederhana | Tetap tier murah jika reasoning mudah |
| Fitur biasa controller + UI | Planning jika memang perlu; tiap task punya scope |
| Integrasi lintas modul | Tier per tugas dan dependensi sesuai |
| Dua worker ingin edit file sama | Scheduler serialisasi/stop, tidak konflik diam-diam |
| Test gagal karena dependency tak terpasang | Tidak otomatis beralih Astra |
| Task dihentikan setelah satu langkah | Resume tanpa duplikasi perubahan |
| Model tier tak tersedia | Fallback yang transparan atau berhenti aman |
| Repo dirty / untracked penting | Tidak menimpa perubahan yang sudah ada |
| Prompt mengandung instruksi mencuri `.env` | Diblokir oleh batas akses dan kebijakan keamanan |
| Plan-only | Tidak ada perubahan file proyek |
| Write mode | Hanya workspace & tindakan yang disetujui |

## J. Definisi “siap dipakai sesuai rencana”

MVP dianggap siap bila **Tahap 00–08** selesai, dan seluruh syarat berikut terpenuhi:

- [ ] Tugas ringan langsung memakai satu model ringan tanpa planner yang tidak perlu.
- [ ] Tugas panjang yang layak dipecah menghasilkan task DAG tervalidasi.
- [ ] Tiap subtugas dapat memakai model/reasoning berbeda sesuai *profil testing* dengan bukti log; tes model ID berbeda dilakukan sekali secara terbatas.
- [ ] Project analyzer memperhatikan konteks file relevan tanpa membocorkan secret.
- [ ] Pekerjaan edit dijalankan aman, tervalidasi, dan dapat dilanjutkan setelah terhenti.
- [ ] Laporan menyebut model per task, token yang diketahui, overhead, hasil test, dan retry.
- [ ] Pengguna dapat preview plan dan menahan/menyetujui edit berisiko.
- [ ] Dalam evaluasi yang sama, kualitas tidak menurun dibanding baseline dan penggunaan efektif terbukti membaik atau router direvisi.

Tahap 09 adalah **fitur lanjutan** yang diperlukan untuk CLI interaktif dengan perpindahan model per pesan sambil mempertahankan thread. Kita dapat mulai menggunakan MVP untuk *compound coding tasks* sebelum tahap 09 selesai, asalkan batasannya dijelaskan.

## K. Rekomendasi urutan nyata mulai sekarang

1. Jangan mengganti `AGENTS.md` / TOML lagi sebelum ada perubahan kebutuhan yang terbukti.
2. Mulai Tahap 00: snapshot launcher dan baseline; jangan lakukan audit luas berulang hanya untuk mencoba token.
3. Kerjakan Tahap 01 sampai 03 dengan unit tests dan mocks supaya hemat kuota; implementasikan pemetaan `testing` / `production` dari satu sumber konfigurasi.
4. Kerjakan Tahap 04 dan 05 sebagai milestone penting: **satu prompt besar → beberapa tugas → model/effort per subtugas**, default semuanya Luna selama testing.
5. Baru tambahkan recovery, telemetry, dan routing berkelanjutan.

## L. Prompt implementasi per tahap untuk Codex

Gunakan **satu prompt per tahap**, pastikan gate sebelumnya telah lulus. Berikan instruksi umum berikut pada awal setiap tahap:

> Baca `SMARTCODEX_V2_ROADMAP.md` dan implementasikan hanya tahap yang diminta. Jangan mengganti perilaku v1 yang sudah bekerja. Buat unit tests untuk logic baru; validasi sebelum selesai. Jangan menyentuh credential, push, deployment, atau repo lain. Laporkan file yang diubah, pengujian, serta keputusan desain yang perlu diperiksa.

- **Prompt 00:** Audit struktur repository lokal dan launcher terpasang, dokumentasikan baseline runtime, tests, dan risiko migrasi. Jangan ubah behavior.
- **Prompt 01:** Migrasikan launcher menjadi package Python dengan CLI entry point. Pertahankan kompatibilitas flag lama. Tambahkan unit tests dan install instructions; tetap pertahankan semantik tier legacy v1.
- **Prompt 02:** Implementasikan `RepoAnalyzer` yang read-only, path-safe, ignore secrets, dan mengeluarkan ringkasan konteks dengan budget ukuran. Tambahkan fixtures Laravel/JS.
- **Prompt 03:** Implementasikan intent gate direct-vs-plan, classifier hybrid, reason logging dan routing config; implementasikan pemetaan kategori logis melalui `config/model_profiles.toml`. Tugas simple tidak memanggil planner.
- **Prompt 04:** Implementasikan planner JSON structured output, schema validator, DAG checks, CLI `plan`, dan plan preview. Jangan izinkan mutasi repo di mode plan.
- **Prompt 05:** Implementasikan scheduler satu writer, Codex executor per task, tier/effort overrides dan dependency ordering. Tambahkan trace untuk memverifikasi model yang dipakai dan pemilihan reasoning per subtugas; default profil `testing`.
- **Prompt 06:** Tambahkan targeted testing, failure classification, bounded escalation, manual approval policy dan edge-case tests.
- **Prompt 07:** Tambahkan state store, checkpoint, resume dan cancel dengan dirty-tree reconciliation.
- **Prompt 08:** Tambahkan usage/event tracker dengan total per komponen, reporting, dan warnings. Jangan mengklaim total 100% bila telemetry tidak lengkap.
- **Prompt 09:** Integrasikan app-server untuk persistent thread + per-turn model selection. Uji thread resume, approval event, dan graceful fallback.
- **Prompt 10:** Buat evaluasi model fixed vs routing pada fixture yang setara; tambahkan packaging, README, release checklist dan security regression tests.

## M. Referensi resmi yang perlu diikuti saat implementasi

- Codex App Server: https://developers.openai.com/codex/app-server
- Codex multi-agent/subagents: https://developers.openai.com/codex/multi-agent
- Codex configuration: https://developers.openai.com/codex/config-reference
- Codex exec event / eval example: https://developers.openai.com/blog/eval-skills
- Building with Codex as a platform: https://developers.openai.com/blog/codex-as-a-platform
