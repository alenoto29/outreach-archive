document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("csv-file");
    const preview = document.getElementById("csv-preview");
    const apply = document.getElementById("csv-apply");
    const result = document.getElementById("csv-result");
    let checkedFile = null;

    input.addEventListener("change", () => {
        checkedFile = null;
        apply.disabled = true;
        result.textContent = "";
    });

    async function upload(dryRun) {
        const file = input.files[0];
        if (!file) {
            result.textContent = "Seleziona un CSV.";
            return;
        }
        preview.disabled = true;
        apply.disabled = true;
        result.textContent = dryRun ? "Controllo in corso…" : "Import in corso…";
        try {
            const form = new FormData();
            form.append("file", file);
            const response = await window.PPN_API.fetch(`/api/import/csv${dryRun ? "?dry_run=1" : ""}`, {
                method: "POST", body: form,
            });
            const data = await response.json();
            if (!response.ok) {
                result.textContent = data.message || `Errore ${response.status}. Serve un account admin.`;
                return;
            }
            const errors = data.errors.map(e => `Riga ${e.row}: ${e.msg}`);
            result.textContent = `${dryRun ? "Anteprima" : "Import completato"}: ${data.created} nuovi, ${data.updated} aggiornati, ${data.skipped} duplicati.\n${errors.join("\n")}`;
            if (dryRun && errors.length === 0 && data.created + data.updated > 0) {
                checkedFile = file;
                apply.disabled = false;
            }
            if (!dryRun) location.reload();
        } catch (error) {
            result.textContent = `Connessione fallita: ${error.message}`;
        } finally {
            preview.disabled = false;
        }
    }

    preview.addEventListener("click", () => upload(true));
    apply.addEventListener("click", () => {
        if (input.files[0] === checkedFile) upload(false);
    });
});
