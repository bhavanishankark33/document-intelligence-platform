/* =========================================================
   DOCULENS — FRONTEND APPLICATION
   Connects the dashboard to the FastAPI backend
   ========================================================= */


/* =========================
   CONFIGURATION
   ========================= */

const API_BASE_URL =
    "https://document-intelligence-platform-kw9e.onrender.com";


/* =========================
   DOM ELEMENTS
   ========================= */

const fileInput = document.getElementById("fileInput");
const documentType = document.getElementById("documentType");
const processBtn = document.getElementById("processBtn");

const selectedFile = document.getElementById("selectedFile");

const progressWrap = document.getElementById("progressWrap");
const progressBar = document.getElementById("progressBar");
const progressLabel = document.getElementById("progressLabel");

const errorBox = document.getElementById("errorBox");

const documentList = document.getElementById("documentList");
const historyList = document.getElementById("historyList");

const refreshBtn = document.getElementById("refreshBtn");
const quickUploadBtn = document.getElementById("quickUploadBtn");

const searchInput = document.getElementById("searchInput");

const totalCount = document.getElementById("totalCount");
const passedCount = document.getElementById("passedCount");
const attentionCount = document.getElementById("attentionCount");
const ocrCount = document.getElementById("ocrCount");

const reviewBadge = document.getElementById("reviewBadge");


/* =========================
   DOCUMENT TYPE LABELS
   ========================= */

const DOCUMENT_TYPE_LABELS = {

    invoice: "Invoice",

    balance_sheet: "Balance Sheet",

    profit_and_loss: "Profit & Loss",

    cash_flow_statement: "Cash Flow Statement"

};


/* =========================
   INITIALIZATION
   ========================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadDocuments();

        setupEventListeners();

    }
);


/* =========================
   EVENT LISTENERS
   ========================= */

function setupEventListeners() {


    /* File selected */

    if (fileInput) {

        fileInput.addEventListener(
            "change",
            handleFileSelection
        );

    }


    /* Process document */

    if (processBtn) {

        processBtn.addEventListener(
            "click",
            processSelectedDocument
        );

    }


    /* Refresh */

    if (refreshBtn) {

        refreshBtn.addEventListener(
            "click",
            loadDocuments
        );

    }


    /* Quick upload */

    if (quickUploadBtn) {

        quickUploadBtn.addEventListener(
            "click",
            () => {

                const uploadSection =
                    document.getElementById(
                        "uploadSection"
                    );

                if (uploadSection) {

                    uploadSection.scrollIntoView({
                        behavior: "smooth"
                    });

                }

            }
        );

    }


    /* Search */

    if (searchInput) {

        searchInput.addEventListener(
            "input",
            filterDocuments
        );

    }

}


/* =========================
   FILE SELECTION
   ========================= */

function handleFileSelection(event) {

    const file = event.target.files[0];

    if (!file) {

        selectedFile.textContent =
            "No document selected.";

        selectedFile.classList.remove(
            "has-file"
        );

        return;

    }


    selectedFile.textContent =
        `${file.name} · ${formatFileSize(file.size)}`;

    selectedFile.classList.add(
        "has-file"
    );


    hideError();

}


/* =========================
   PROCESS DOCUMENT
   ========================= */

async function processSelectedDocument() {

    const file = fileInput.files[0];

    const type = documentType.value;


    if (!file) {

        showError(
            "Please choose a document before processing."
        );

        return;

    }


    if (!isSupportedFile(file)) {

        showError(
            "Unsupported file. Please upload a PDF, JPG, or PNG document."
        );

        return;

    }


    const formData = new FormData();

    formData.append(
        "file",
        file
    );

    formData.append(
        "document_type",
        type
    );


    setProcessingState(true);

    hideError();


    try {

        updateProgress(
            15,
            "Uploading document…"
        );


        await delay(350);


        updateProgress(
            30,
            "Validating document…"
        );


        await delay(350);


        updateProgress(
            50,
            "Extracting text with OCR…"
        );


        const response = await fetch(
            `${API_BASE_URL}/api/v1/documents/process`,
            {
                method: "POST",
                body: formData
            }
        );


        updateProgress(
            75,
            "Running AI extraction…"
        );


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                extractApiError(data)
            );

        }


        updateProgress(
            90,
            "Running financial validation…"
        );


        await delay(350);


        updateProgress(
            100,
            "Processing completed."
        );


        await delay(400);


        /*
         * Store the result temporarily so the result
         * page can display it immediately.
         */

        sessionStorage.setItem(
            "lastDocumentResult",
            JSON.stringify(data)
        );


        /*
         * Navigate to the document review page.
         */

        window.location.href =
            `/document?name=${encodeURIComponent(
                data.document.document_name
            )}`;


    } catch (error) {

        console.error(
            "Document processing error:",
            error
        );


        showError(
            error.message ||
            "Unable to process the document."
        );


        setProcessingState(false);

    }

}


/* =========================
   LOAD DOCUMENTS
   ========================= */

async function loadDocuments() {

    try {

        documentList.innerHTML = `
            <div class="empty-state">
                Loading documents…
            </div>
        `;


        const response = await fetch(
            `${API_BASE_URL}/api/v1/documents`
        );


        if (!response.ok) {

            throw new Error(
                "Unable to load documents."
            );

        }


        const data = await response.json();


        renderDocuments(
            data.documents || []
        );


        updateDashboardStats(
            data.documents || []
        );


        renderHistory(
            data.documents || []
        );


    } catch (error) {

        console.error(
            "Loading documents failed:",
            error
        );


        documentList.innerHTML = `
            <div class="empty-state">
                Unable to load documents.
                <br>
                Make sure the FastAPI backend is running.
            </div>
        `;

    }

}


/* =========================
   RENDER DOCUMENTS
   ========================= */

function renderDocuments(documents) {

    if (!documents.length) {

        documentList.innerHTML = `
            <div class="empty-state">
                No documents have been processed yet.
            </div>
        `;

        return;

    }


    documentList.innerHTML =
        documents.map(
            document => {

                const typeLabel =
                    DOCUMENT_TYPE_LABELS[
                        document.document_type
                    ] ||
                    document.document_type;


                const statusClass =
                    getStatusClass(
                        document.processing_status
                    );


                const statusLabel =
                    formatStatus(
                        document.processing_status
                    );


                const date =
                    formatDate(
                        document.created_at
                    );


                return `

                    <div
                        class="document-row"
                        data-name="${escapeHtml(
                            document.document_name
                        )}"
                    >

                        <div class="document-name">

                            <div class="document-icon">
                                ▤
                            </div>

                            <div>

                                <div class="document-title">
                                    ${escapeHtml(
                                        document.document_name
                                    )}
                                </div>

                                <div class="document-meta">

                                    ${document.page_count || 0}
                                    page${document.page_count === 1 ? "" : "s"}

                                    ·

                                    ${formatFileType(
                                        document.file_type
                                    )}

                                </div>

                            </div>

                        </div>


                        <div class="document-type">

                            ${escapeHtml(
                                typeLabel
                            )}

                        </div>


                        <div>

                            <span
                                class="status-badge ${statusClass}"
                            >

                                ${statusLabel}

                            </span>

                        </div>


                        <div class="document-date">

                            ${date}

                        </div>


                        <button
                            class="open-btn"
                            onclick="openDocument(
                                '${encodeURIComponent(
                                    document.document_name
                                )}'
                            )"
                        >

                            View

                        </button>

                    </div>

                `;

            }
        ).join("");

}


/* =========================
   DASHBOARD STATISTICS
   ========================= */

function updateDashboardStats(documents) {

    const total =
        documents.length;


    const passed =
        documents.filter(
            document =>
                document.processing_status === "PASS"
        ).length;


    const attention =
        documents.filter(
            document =>
                document.processing_status === "FAIL" ||
                document.processing_status === "FAILED" ||
                document.processing_status === "NEEDS_REVIEW"
        ).length;


    const ocrDocuments =
        documents.filter(
            document =>
                document.ocr_used === true
        ).length;


    if (totalCount) {

        totalCount.textContent =
            total;

    }


    if (passedCount) {

        passedCount.textContent =
            passed;

    }


    if (attentionCount) {

        attentionCount.textContent =
            attention;

    }


    if (ocrCount) {

        ocrCount.textContent =
            ocrDocuments;

    }


    if (reviewBadge) {

        reviewBadge.textContent =
            attention;

    }

}


/* =========================
   HISTORY
   ========================= */

function renderHistory(documents) {

    if (!historyList) {

        return;

    }


    if (!documents.length) {

        historyList.innerHTML = `
            <div class="empty-state">
                No activity yet.
            </div>
        `;

        return;

    }


    const recentDocuments =
        documents.slice(0, 6);


    historyList.innerHTML =
        recentDocuments.map(
            document => {

                const status =
                    formatStatus(
                        document.processing_status
                    );


                const icon =
                    document.processing_status === "PASS"
                        ? "✓"
                        : "!";


                return `

                    <div class="history-item">

                        <div class="history-icon">

                            ${icon}

                        </div>


                        <div class="history-text">

                            <strong>

                                ${escapeHtml(
                                    document.document_name
                                )}

                            </strong>


                            <span>

                                Processing completed ·
                                ${status}

                            </span>

                        </div>


                        <div class="history-time">

                            ${formatDate(
                                document.created_at
                            )}

                        </div>

                    </div>

                `;

            }
        ).join("");

}


/* =========================
   OPEN DOCUMENT
   ========================= */

function openDocument(encodedName) {

    window.location.href =
        `/document?name=${encodedName}`;

}


/* =========================
   SEARCH
   ========================= */

function filterDocuments() {

    const search =
        searchInput.value
            .trim()
            .toLowerCase();


    const rows =
        document.querySelectorAll(
            ".document-row"
        );


    rows.forEach(
        row => {

            const name =
                row.dataset.name
                    .toLowerCase();


            if (
                !search ||
                name.includes(search)
            ) {

                row.style.display =
                    "grid";

            } else {

                row.style.display =
                    "none";

            }

        }
    );

}


/* =========================
   PROCESSING UI
   ========================= */

function setProcessingState(isProcessing) {

    if (!processBtn) {

        return;

    }


    processBtn.disabled =
        isProcessing;


    if (isProcessing) {

        processBtn.textContent =
            "Processing…";


        progressWrap.classList.remove(
            "hidden"
        );

    } else {

        processBtn.textContent =
            "Process document";


        progressWrap.classList.add(
            "hidden"
        );

    }

}


function updateProgress(
    percentage,
    message
) {

    if (progressBar) {

        progressBar.style.width =
            `${percentage}%`;

    }


    if (progressLabel) {

        progressLabel.textContent =
            message;

    }

}


function showError(message) {

    if (!errorBox) {

        return;

    }


    errorBox.textContent =
        message;


    errorBox.classList.remove(
        "hidden"
    );

}


function hideError() {

    if (!errorBox) {

        return;

    }


    errorBox.classList.add(
        "hidden"
    );

}


/* =========================
   FILE HELPERS
   ========================= */

function isSupportedFile(file) {

    const allowedTypes = [
        "application/pdf",
        "image/jpeg",
        "image/png"
    ];


    const allowedExtensions = [
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png"
    ];


    const name =
        file.name.toLowerCase();


    const extension =
        allowedExtensions.some(
            extension =>
                name.endsWith(extension)
        );


    return (
        allowedTypes.includes(
            file.type
        ) ||
        extension
    );

}


function formatFileSize(bytes) {

    if (bytes === 0) {

        return "0 Bytes";

    }


    const units = [
        "Bytes",
        "KB",
        "MB",
        "GB"
    ];


    const index =
        Math.floor(
            Math.log(bytes) /
            Math.log(1024)
        );


    return (
        parseFloat(
            (
                bytes /
                Math.pow(
                    1024,
                    index
                )
            ).toFixed(1)
        ) +
        " " +
        units[index]
    );

}


function formatFileType(type) {

    if (!type) {

        return "FILE";

    }


    if (
        type ===
        "application/pdf"
    ) {

        return "PDF";

    }


    if (
        type ===
        "image/jpeg"
    ) {

        return "JPG";

    }


    if (
        type ===
        "image/png"
    ) {

        return "PNG";

    }


    return type
        .split("/")
        .pop()
        .toUpperCase();

}


/* =========================
   STATUS HELPERS
   ========================= */

function getStatusClass(status) {

    switch (
        String(status).toUpperCase()
    ) {

        case "PASS":
            return "pass";

        case "FAIL":
        case "FAILED":
            return "fail";

        case "NEEDS_REVIEW":
            return "review";

        case "NOT_APPLICABLE":
            return "na";

        case "UNSUPPORTED":
            return "unsupported";

        default:
            return "na";

    }

}


function formatStatus(status) {

    const value =
        String(status || "")
            .toUpperCase();


    switch (value) {

        case "PASS":
            return "PASS";

        case "FAIL":
        case "FAILED":
            return "FAILED";

        case "NEEDS_REVIEW":
            return "NEEDS REVIEW";

        case "NOT_APPLICABLE":
            return "NOT APPLICABLE";

        case "UNSUPPORTED":
            return "UNSUPPORTED";

        default:
            return value || "UNKNOWN";

    }

}


/* =========================
   DATE
   ========================= */

function formatDate(dateString) {

    if (!dateString) {

        return "—";

    }


    const date =
        new Date(dateString);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return "—";

    }


    return date.toLocaleString(
        [],
        {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        }
    );

}


/* =========================
   API ERROR
   ========================= */

function extractApiError(data) {

    if (!data) {

        return "The server returned an unknown error.";

    }


    if (
        typeof data.detail ===
        "string"
    ) {

        return data.detail;

    }


    if (
        data.detail &&
        data.detail.message
    ) {

        return data.detail.message;

    }


    if (
        data.message
    ) {

        return data.message;

    }


    return "The document could not be processed.";

}


/* =========================
   UTILITIES
   ========================= */

function delay(milliseconds) {

    return new Promise(
        resolve =>
            setTimeout(
                resolve,
                milliseconds
            )
    );

}


function escapeHtml(value) {

    return String(value ?? "")
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}