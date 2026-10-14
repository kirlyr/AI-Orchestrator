
## Model Selection
- FAST: Simple and well-defined work -> fast_worker.
- STANDARD: Routine implementation -> standard_worker.
- DEEP: Complex reasoning -> deep_worker.
- CRITICAL: Report the need for stronger reasoning to the parent.
- The parent agent owns all escalation decisions.
- Do not escalate based on prompt length or file count alone.

## Execution
- Prefer completing simple tasks directly.
- Delegate only when a bounded independent task benefits from a separate worker.
- Do not delegate to a worker using the same model and effort unless there is a clear benefit.
- Avoid repeated repository exploration.
- Assign clear file ownership before parallel edits.
- Never overwrite another worker's uncommitted changes.
- Return concise findings, changed files, and test results.

## Escalation
- Escalate only after identifying a concrete blocker, failed validation, or reasoning limitation.
- Prefer FAST -> STANDARD -> DEEP when necessary.
- The parent decides whether escalation is justified.
- Allow at most one escalation per subtask by default.
- Do not retry the same failed approach without new evidence.
- Preserve findings when handing work to another worker.
- Do not start another agent solely to confirm an obvious result.
```

Batas satu eskalasi merupakan **kebijakan penghematan yang kita tetapkan sendiri**, bukan batas otomatis dari Codex.

### Perbaiki juga Fast Worker

Di `.codex/agents/fast-worker.toml`, ubah instruksi eskalasinya yang sekarang terlalu bergantung pada jumlah modul menjadi:

```toml
developer_instructions = """
Work only on the assigned bounded task.
Reuse findings and paths provided by the parent.
Prefer minimal changes and targeted verification.
Do not escalate merely because multiple files are involved.
Report concrete blockers, risky dependencies,
or reasoning limitations to the parent.
Do not deploy or modify production data.
"""
```

Untuk `.codex/config.toml`, **belum perlu ada perubahan**. Nilai `max_concurrent_threads_per_session = 2` sudah membatasi jumlah subagent yang berjalan bersamaan, walaupun tidak membatasi total token ataupun delegasi berurutan. <Cite ref="turn819054view2"/>

## 4. Kenapa auditnya bisa banyak memakai token?

Berdasarkan log, Codex melakukan beberapa aktivitas tambahan selain membaca lima file konfigurasi:

- Membaca skill OpenAI Docs dari instalasi lokal.
- Melakukan beberapa pencarian dokumentasi resmi.
- Memeriksa konfigurasi dengan perintah terminal dan Python.
- Melakukan pemeriksaan ulang struktur dan menyusun audit.

Semuanya dapat berguna untuk audit menyeluruh, tetapi untuk pemeriksaan yang sempit, sebagian pekerjaan tersebut mungkin tidak diperlukan.

Ke depan, kita sebaiknya menginstruksikan pekerjaan audit secara lebih terarah. Contohnya:

```powershell
smartcodex "Periksa konsistensi nama agent dan konfigurasi model pada AGENTS.md dan 4 file TOML. Fokus pada file lokal. Jangan mengubah file, jangan membuat subagent, dan gunakan dokumentasi eksternal hanya jika perlu memverifikasi hal yang belum pasti. Laporkan maksimal 8 poin." --router ai --mode exec
```

Ini tidak menjamin batas token tertentu, tetapi membantu membatasi cakupan pekerjaan.

## 5. Apa tahap berikutnya?

Menurutku **jangan langsung mengembangkan SmartCodex v2 dulu**. Kita sudah membuktikan dua tingkatan routing:

<box border radius="lg" padding={3} gap={2}>
  <text weight="medium" size="sm">Hasil dua pengujian nyata</text>
  <table>
    <table-row>
      <table-cell>
        **Membaca README**
        <text color="secondary" size="xs">Tugas sederhana</text>
      </table-cell>
      <table-cell>
        <text size="sm">Luna Low</text>
        <text color="secondary" size="xs" tabularNums>8.033 token</text>
      </table-cell>
    </table-row>
    <table-row>
      <table-cell>
        **Audit konfigurasi**
        <text color="secondary" size="xs">Tugas lebih kompleks</text>
      </table-cell>
      <table-cell>
        <text size="sm">Sol Medium</text>
        <text color="secondary" size="xs" tabularNums>95.657 token</text>
      </table-cell>
    </table-row>
  </table>
  <caption>Penggunaan dua pekerjaan yang berbeda, sehingga tidak bisa dibandingkan langsung sebagai ukuran efisiensi.</caption>
</box>

Berikutnya kita perlu membuktikan bahwa **subagent benar-benar aktif dan memilih model berbeda ketika menjalankan satu pekerjaan besar**.

Saran urutannya: perbaiki `AGENTS.md` dan `fast-worker.toml` terlebih dahulu, lalu uji delegasi dengan satu tugas coding nyata yang memiliki dua subtugas independen.

**Kesimpulannya:** SmartCodex sudah berhasil memilih model utama berdasarkan tingkat kesulitan prompt. Sekarang fokus kita adalah mengurangi delegasi yang tidak perlu, mengontrol eskalasi, dan mengukur apakah multi-agent benar-benar menghemat penggunaan dibandingkan satu model saja.