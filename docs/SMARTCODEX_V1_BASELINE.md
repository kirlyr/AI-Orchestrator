# SmartCodex v1 — Snapshot & Baseline

**Tanggal pemeriksaan:** 14 Oktober 2026  
**Sumber v1:** `C:\tools\smartcodex` (inspeksi read-only)  
**Cakupan:** Tahap 00 pada `SMARTCODEX_V2_ROADMAP.md` saja.

## Ringkasan status

Launcher v1 dan tes lokalnya dapat dijalankan. Tujuh unit test lulus. Source instalasi tidak diubah; snapshot dicatat sebagai inventaris file dan SHA-256 di bawah. Baseline ini **parsial**: eksekusi tugas nyata dengan `codex exec`, verifikasi output tugas, metrik waktu/token, status autentikasi/login, dan akses model pada sesi kerja tidak diuji. Tidak ada tugas read-only yang dikirim ke model sehingga tidak ada kuota AI yang digunakan.

**Gate Tahap 00: belum lulus penuh.** Syarat integritas source dan baseline test lokal terpenuhi, tetapi baseline runtime terkendali yang diminta roadmap belum lengkap. Tidak ada perubahan file production atau launcher.

## Lingkungan dan keadaan repository

| Pemeriksaan | Hasil |
| --- | --- |
| Repo kerja | `D:\atsal\AI-Orchestrator` |
| Branch / HEAD | `main` / `69574be5b5c04d3401a59b7ac6bf012b172c3351` |
| Working tree sebelum/sesudah pemeriksaan | Bersih (`git status --short --branch`: `## main...origin/main`) |
| Python | `py -3 --version` → Python 3.13.15; perintah `python` mengarah ke Windows Store alias yang tidak tersedia |
| Codex CLI | `codex --version` → `codex-cli 0.162.1` |
| Login | Tidak diperiksa; tidak membaca credential atau menjalankan login |
| Model tersedia/dapat dipanggil | Tidak diverifikasi melalui task runtime. `codex debug models` tidak dijalankan karena outputnya memuat instruksi internal yang tidak dibutuhkan untuk baseline |

CLI legacy yang terlihat langsung dari parser: positional prompt atau `--file`; `--router smart|rules|ai` (default `smart`); `--mode chat|exec|loop` (default `chat`); `--force-tier luna-low|sol-low|sol-medium|sol-high|astra-high`; `--allow-astra`; `--write`; `--dry-run`.

## Snapshot instalasi v1

Snapshot tidak dibuat dengan menyalin file karena sumber berada di direktori instalasi terpisah. Inventaris plus hash ini merekam identitas byte source pada saat pemeriksaan; seluruh file dibaca saja.

| File | Byte | SHA-256 |
| --- | ---: | --- |
| `README.md` | 4209 | `D9EECAFB532073BA226781F31E9F9BC01C91F6884CA85ACE4EBE40A745ED6EF2` |
| `smartcodex.ps1` | 235 | `360B1DE27B966F762C9F5827C4A5D95B5702D29A651DCA66A1824FCD0F739AB7` |
| `smartcodex.py` | 11498 | `EF88C4A4E8375991FF2CE34BDCD428CC54CB6209BA6DD648D5BF83005513E6DC` |
| `test_smartcodex.py` | 1103 | `8828B4637A416C1799C9C961013D490DB61131E462FF1B19CF1030578CFE666F` |

Direktori `smartcodex-launcher` ada tetapi kosong. File konfigurasi runtime tidak ditemukan di folder instalasi. Snapshot ini bukan salinan pemulihan; hash dapat dipakai untuk memverifikasi source yang sama.

## Fitur yang sudah berjalan menurut source dan test

- Routing lokal berbasis regex untuk sinyal tugas sederhana, rutin, kompleks, dan berisiko; tier dipetakan ke model serta reasoning: Luna Low, Sol Low/Medium/High, dan Astra High.
- Router `smart` memakai aturan dahulu dan hanya memanggil classifier ketika confidence aturan tidak tinggi. `rules` menghindari classifier AI; `ai` selalu mencoba classifier Luna Low. Kegagalan classifier jatuh kembali ke aturan lokal.
- Classifier membatasi prompt sampai 7000 karakter, mengirim permintaan JSON-schema melalui `codex exec` pada sandbox read-only di temp directory, dan tidak menyertakan konteks repository.
- Astra dibatasi ke Sol High kecuali `--allow-astra` diberikan. `--force-tier` dapat memilih tier secara eksplisit.
- Mode `chat` membuka Codex TUI dengan prompt awal setelah satu kali routing. Mode `exec` menjalankan satu tugas; sandbox default read-only dan `--write` mengizinkan workspace-write. Mode `loop` membuat sesi exec baru untuk tiap prompt, tanpa riwayat percakapan bersama.
- `--dry-run` menampilkan keputusan aturan lokal tanpa menjalankan classifier atau Codex. PowerShell shim meneruskan argumen ke Python launcher.
- README menyatakan tidak perlu paket Python pihak ketiga dan menggunakan login Codex.

Hasil test otomatis: `py -3 -m unittest discover -s C:\tools\smartcodex -p test_smartcodex.py` → **Ran 7 tests; OK** (0.006s). Test meliputi rute sederhana/rutin/berisiko, cap Astra, dry-run, prompt kosong, dan tidak memakai AI pada rute smart dengan confidence tinggi. Tidak ada test yang menjalankan subprocess Codex sesungguhnya.

## Keterbatasan yang teramati

- Hanya prompt awal yang diroute pada sesi `chat`; follow-up tetap di model yang sama. Mode loop menghapus konteks antar-prompt.
- Routing berbasis kata kunci dan tidak menganalisis struktur atau isi repository. Kata kunci dan batas panjang dapat salah mengklasifikasikan kebutuhan.
- Mode `ai` menambah satu panggilan model dan overhead; keseluruhan token classifier + executor tidak dilaporkan oleh launcher.
- Tidak ada planner, pembagian subtugas, routing per subtugas, DAG, checkpoint/resume, state store, telemetry, atau verifier otomatis.
- Tidak ada kontrol eksplisit jumlah subtugas/penulis karena delegasi bukan kemampuan launcher v1.
- Ketersediaan model bergantung akun/runtime. README memperingatkan akses Astra bergantung pada akun; belum diuji dalam baseline ini.
- “Tanpa paket eksternal” didukung oleh source yang memakai standard library dan test berhasil di Python 3.13.15; matriks Python 3.10+ belum diuji.

## Risiko migrasi ke v2

1. **Kompatibilitas CLI dan semantik tier:** pertahankan nama flag lama dan makna legacy `--force-tier sol-low` sebagai Sol Low. Jangan diam-diam memetakannya ke model lain.
2. **Perubahan routing:** regex precedence, ambang confidence, batas prompt, dan fallback adalah perilaku yang telah ada. Perubahan dapat mengubah model yang dipilih untuk prompt lama.
3. **Keselamatan subprocess/sandbox:** classifier dan executor memakai argumen list tanpa shell; classifier read-only di temp directory. Pertahankan isolasi dan default executor read-only, serta uji quoting/argumen Windows.
4. **Kontrak input/output:** classifier mengharapkan JSON dengan `tier` dan `reason`; executor memakai stdin untuk prompt pada mode exec. Perubahan protokol dapat merusak kompatibilitas runtime.
5. **Akses premium:** tier Astra memerlukan opt-in; fallback otomatis ke model lebih mahal tidak boleh diperkenalkan tanpa persetujuan.
6. **Biaya/telemetri:** routing AI memerlukan panggilan model tambahan; v1 tidak menjumlahkan token atau retries sehingga perbandingan efisiensi perlu instrumen baru.
7. **State dan perubahan pengguna:** v1 belum menyimpan status task atau merekonsiliasi dirty tree. Migrasi ke writer/scheduler harus menjaga perubahan kerja yang sudah ada dan membatasi operasi pada workspace.
8. **Jalur instalasi:** launcher aktif berada di `C:\tools\smartcodex`, di luar repo pengembangan. Perubahan di repo tidak otomatis mengubah instalasi; migrasi perlu proses pemindahan/pemasangan yang eksplisit.

## Baseline runtime yang belum diukur

Roadmap meminta beberapa tugas read-only dengan model, exit code, waktu, token (jika tersedia), dan hasil verifikasi, serta catatan jenis login dan model yang dapat dijalankan. Pemeriksaan ini sengaja tidak menjalankan tugas Codex karena akan memakai kuota dan memerlukan autentikasi/model runtime. Karena itu nilai-nilai tersebut **belum tersedia**, bukan nol. Sebelum memakai baseline untuk perbandingan v2, jalankan contoh tugas yang sama secara terkontrol dan catat sesi, model/effort aktual dari trace, exit code, durasi, token yang dilaporkan (atau unknown), dan pemeriksaan hasil.

## Keputusan gate Tahap 00

| Kriteria | Status |
| --- | --- |
| Source v1 terinventarisasi dan identitas hash tersimpan | Lulus |
| Launcher tidak diubah; working tree bersih | Lulus |
| Baseline test lokal tercatat | Lulus (7/7) |
| Baseline runtime read-only dengan model/exit/time/token/verifikasi | Belum dilakukan |
| Login dan model aktual yang dapat dijalankan tercatat | Belum diverifikasi |
| **Tahap 00 keseluruhan** | **Belum lulus penuh; baseline runtime masih perlu dilengkapi** |
