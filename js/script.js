
/* =========================================
   COLLEGECONNECT - MAIN JAVASCRIPT
   Flask API + MySQL Integration
========================================= */

const API_BASE_URL = window.COLLEGECONNECT_API_BASE_URL;

document.addEventListener("DOMContentLoaded", () => {

    // =========================================
    // COMMON HELPERS
    // =========================================

    function escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[character]);
    }

    function formatLabel(value) {
        return String(value ?? "")
            .replace(/_/g, " ")
            .replace(/\b\w/g, letter => letter.toUpperCase());
    }

    function formatDate(value) {
        if (!value) return "Unknown";

        const date = new Date(value);

        return Number.isNaN(date.getTime())
            ? String(value)
            : date.toLocaleString();
    }

    function setText(id, value) {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    }

    async function fetchJSON(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            credentials: "include"
        });

        const data = await response.json();

        if (!response.ok) {
            const error = new Error(data.error || "Request failed.");
            error.status = response.status;
            throw error;
        }

        return data;
    }

    // =========================================
    // USER ROLE / PROFILE
    // =========================================

    let currentRole = "student";
    let currentUser = null;

    async function initializeUserRole() {
        try {
            const result = await fetchJSON(
                `${API_BASE_URL}/api/me`
            );

            currentUser = result.user || result;
            currentRole = String(
                currentUser.role || "student"
            ).toLowerCase();

            const roleLabels = {
                student: "Student",
                cr: "Class Representative",
                professor: "Professor",
                admin: "Admin"
            };

            setText("profileName", currentUser.name || "User");
            setText(
                "profileRole",
                roleLabels[currentRole] || formatLabel(currentRole)
            );

            const avatar = document.getElementById("profileAvatar");
            if (avatar) {
                avatar.textContent =
                    (currentUser.name || "U").charAt(0).toUpperCase();
            }
        } catch (error) {
            if (
                error.status === 401 &&
                document.body.dataset.requiresAuth === "true"
            ) {
                window.location.replace("login.html");
                return false;
            }
            console.warn("Could not retrieve user profile:", error);
        }

        configureRoleInterface();
        return true;
    }

    function configureRoleInterface() {
        const reportButton = document.getElementById("openComplaintForm");
        const emptyReportButton = document.getElementById("emptyReportBtn");
        const resolutionProcess = document.getElementById("resolutionProcess");

        if (currentRole === "professor") {
            if (reportButton) reportButton.style.display = "none";
            if (emptyReportButton) emptyReportButton.style.display = "none";

            setText("complaintsPageTitle", "Assigned Complaints");
            setText(
                "complaintsPageDescription",
                "Review your assigned complaints and update their resolution status."
            );
            setText("complaintListHeading", "My Assigned Issues");
        }

        if (currentRole === "student") {
            setText(
                "complaintsPageDescription",
                "Report campus issues and track their resolution."
            );
        }

        if (resolutionProcess && currentRole === "professor") {
            resolutionProcess.style.display = "none";
        }
    }

    // =========================================
    // COMPLAINT MODAL
    // =========================================

    const modal = document.getElementById("complaintModal");
    const openBtn = document.getElementById("openComplaintForm");
    const emptyReportBtn = document.getElementById("emptyReportBtn");
    const closeBtn = document.getElementById("closeComplaintForm");
    const cancelBtn = document.getElementById("cancelComplaint");
    const complaintForm = document.getElementById("complaintForm");

    function openComplaintModal() {
        if (!modal || currentRole === "professor") return;

        modal.classList.add("show");
        document.body.style.overflow = "hidden";
    }

    function closeComplaintModal() {
        if (!modal) return;

        modal.classList.remove("show");
        document.body.style.overflow = "";
    }

    openBtn?.addEventListener("click", openComplaintModal);
    emptyReportBtn?.addEventListener("click", openComplaintModal);
    closeBtn?.addEventListener("click", closeComplaintModal);
    cancelBtn?.addEventListener("click", closeComplaintModal);

    modal?.addEventListener("click", event => {
        if (event.target === modal) closeComplaintModal();
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") closeComplaintModal();
    });

    // =========================================
    // COMPLAINT FILTERS
    // =========================================

    const statusFilter = document.getElementById("statusFilter");
    const categoryFilter = document.getElementById("categoryFilter");

    function applyComplaintFilters() {
        const cards = document.querySelectorAll(".complaint-card");
        const selectedStatus = statusFilter?.value || "";
        const selectedCategory = categoryFilter?.value || "";

        cards.forEach(card => {
            const matchesStatus =
                !selectedStatus || card.dataset.status === selectedStatus;

            const matchesCategory =
                !selectedCategory || card.dataset.category === selectedCategory;

            card.hidden = !(matchesStatus && matchesCategory);
        });
    }

    statusFilter?.addEventListener("change", applyComplaintFilters);
    categoryFilter?.addEventListener("change", applyComplaintFilters);

    // =========================================
    // COMPLAINT STATISTICS
    // =========================================

    function updateComplaintStats(complaints) {
        const counts = {
            total: complaints.length,
            pending: 0,
            in_progress: 0,
            resolved: 0
        };

        complaints.forEach(complaint => {
            const status = String(complaint.status || "").toLowerCase();

            if (Object.prototype.hasOwnProperty.call(counts, status)) {
                counts[status]++;
            }
        });

        setText("totalComplaints", counts.total);
        setText("pendingComplaints", counts.pending);
        setText("inProgressComplaints", counts.in_progress);
        setText("resolvedComplaints", counts.resolved);
    }

    // =========================================
    // CR: LOAD FACULTY AND ASSIGN COMPLAINTS
    // =========================================

    async function loadFacultyOptions() {
        if (currentRole !== "cr") return;

        const selects = document.querySelectorAll(".faculty-select");
        if (!selects.length) return;

        try {
            const faculty = await fetchJSON(
                `${API_BASE_URL}/api/faculty`
            );

            selects.forEach(select => {
                const previousValue = select.value;

                select.replaceChildren(
                    new Option("Select faculty", "")
                );

                faculty.forEach(person => {
                    select.add(new Option(person.name, person.id));
                });

                if ([...select.options].some(
                    option => option.value === previousValue
                )) {
                    select.value = previousValue;
                }
            });
        } catch (error) {
            console.error("Faculty list error:", error);

            document.querySelectorAll(".assign-controls").forEach(
                controls => controls.remove()
            );
        }
    }

    async function assignComplaint(button) {
        if (currentRole !== "cr") return;

        const complaintId = button.dataset.complaintId;
        const card = button.closest(".complaint-card");
        const select = card?.querySelector(".faculty-select");
        const message = card?.querySelector(".assign-message");

        if (!select?.value) {
            if (message) {
                message.textContent = "Please select a faculty member.";
                message.className = "assign-message error";
            }
            return;
        }

        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = "Assigning...";

        if (message) message.textContent = "";

        try {
            const result = await fetchJSON(
                `${API_BASE_URL}/api/complaints/${complaintId}/assign`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        faculty_id: Number(select.value)
                    })
                }
            );

            if (message) {
                message.textContent =
                    result.message || "Complaint assigned successfully.";
                message.className = "assign-message success";
            }

            await loadComplaints();
        } catch (error) {
            console.error("Assignment error:", error);

            if (message) {
                message.textContent = error.message;
                message.className = "assign-message error";
            }
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    document.addEventListener("click", event => {
        const button = event.target.closest(".assign-complaint-btn");
        if (button) assignComplaint(button);
    });

    // =========================================
    // LOAD COMPLAINTS FROM MYSQL
    // =========================================

    async function loadComplaints() {
        const complaintsList = document.getElementById("complaintsList");
        let complaints = [];

        try {
            if (currentRole === "professor") {
                complaints = await fetchJSON(
                    `${API_BASE_URL}/api/my-complaints`
                );
            } else {
                complaints = await fetchJSON(
                    `${API_BASE_URL}/api/complaints`
                );
            }

            window.collegeConnectComplaints = complaints;
            updateComplaintStats(complaints);

            if (!complaintsList) return complaints;

            if (!complaints.length) {
                complaintsList.innerHTML = `
                    <div class="empty-state">
                        <h3>${currentRole === "professor"
                            ? "No complaints assigned to you"
                            : "No complaints reported yet"}</h3>
                        <p>${currentRole === "professor"
                            ? "Your assigned complaints will appear here."
                            : "Reported issues will appear here."}</p>
                    </div>`;
                return complaints;
            }

            complaintsList.innerHTML = complaints.map(complaint => {
                const assignmentControls = currentRole === "cr" ? `
                    <div class="assign-controls">
                        <label for="faculty-${escapeHTML(complaint.id)}">
                            Assign to Faculty
                        </label>
                        <select id="faculty-${escapeHTML(complaint.id)}"
                                class="faculty-select">
                            <option value="">Loading faculty...</option>
                        </select>
                        <button type="button"
                                class="assign-complaint-btn"
                                data-complaint-id="${escapeHTML(complaint.id)}">
                            Assign Complaint
                        </button>
                        <p class="assign-message" aria-live="polite"></p>
                    </div>` : "";

                const professorControls =
                    currentRole === "professor" &&
                    complaint.status !== "resolved" ? `
                    <div class="professor-status-controls">
                        <button type="button"
                                class="resolve-complaint-btn"
                                data-complaint-id="${escapeHTML(complaint.id)}">
                            Mark as Resolved
                        </button>
                        <p class="status-update-message"
                           aria-live="polite"></p>
                    </div>` : "";

                return `
                    <article class="complaint-card"
                        data-status="${escapeHTML(complaint.status)}"
                        data-category="${escapeHTML(complaint.category)}">

                        <div class="complaint-card-header">
                            <h3>${escapeHTML(complaint.title)}</h3>
                            <span class="complaint-status status-${escapeHTML(complaint.status)}">
                                ${escapeHTML(formatLabel(complaint.status))}
                            </span>
                        </div>

                        <p>${escapeHTML(complaint.description)}</p>

                        <div class="complaint-meta">
                            <span>Complaint ID: ${escapeHTML(complaint.id)}</span>
                            <span>Category: ${escapeHTML(complaint.category)}</span>
                            <span>Location: ${escapeHTML(complaint.location || "Not specified")}</span>
                            <span>Priority: ${escapeHTML(formatLabel(complaint.priority))}</span>
                            <span>Reported: ${escapeHTML(formatDate(complaint.created_at))}</span>
                            <span>Assigned Faculty: ${escapeHTML(complaint.assigned_faculty_name || "Not assigned")}</span>
                        </div>

                        ${assignmentControls}
                        ${professorControls}
                    </article>`;
            }).join("");

            applyComplaintFilters();

            if (currentRole === "cr") {
                await loadFacultyOptions();
            }

            return complaints;

        } catch (error) {
            console.error("Error loading complaints:", error);

            if (complaintsList) {
                complaintsList.innerHTML = `
                    <div class="empty-state">
                        <h3>Unable to load complaints</h3>
                        <p>${escapeHTML(error.message)}</p>
                    </div>`;
            }

            return [];
        }
    }

    // =========================================
    // PROFESSOR: UPDATE COMPLAINT STATUS
    // =========================================

    document.addEventListener("click", async event => {
        const button = event.target.closest(".resolve-complaint-btn");
        if (!button) return;

        if (currentRole !== "professor") {
            alert("Only professors can resolve assigned complaints.");
            return;
        }

        const complaintId = button.dataset.complaintId;
        const card = button.closest(".complaint-card");
        const message = card?.querySelector(".status-update-message");

        if (!confirm("Mark this complaint as resolved?")) return;

        button.disabled = true;
        button.textContent = "Updating...";

        try {
            const result = await fetchJSON(
                `${API_BASE_URL}/api/complaints/${complaintId}/status`,
                {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        status: "resolved"
                    })
                }
            );

            if (message) {
                message.textContent =
                    result.message || "Complaint marked as resolved.";
                message.className = "status-update-message success";
            }

            await loadComplaints();

        } catch (error) {
            console.error("Status update error:", error);

            if (message) {
                message.textContent = error.message;
                message.className = "status-update-message error";
            }

            button.disabled = false;
            button.textContent = "Mark as Resolved";
        }
    });

    // =========================================
    // SUBMIT COMPLAINT
    // =========================================

    if (complaintForm) {
        complaintForm.addEventListener("submit", async event => {
            event.preventDefault();

            if (currentRole === "professor") {
                alert("Professors cannot submit complaints from this page.");
                return;
            }

            const submitBtn = complaintForm.querySelector(
                ".submit-btn, button[type='submit'], input[type='submit']"
            );

            const originalText = submitBtn
                ? (submitBtn.tagName === "INPUT"
                    ? submitBtn.value
                    : submitBtn.textContent)
                : "";

            const formData = new FormData(complaintForm);

            const complaint = {
                category: formData.get("category")?.toString().trim() || "",
                location: formData.get("location")?.toString().trim() || "",
                title: formData.get("title")?.toString().trim() || "",
                description: formData.get("description")?.toString().trim() || "",
                priority: formData.get("priority")?.toString().toLowerCase() || "medium"
            };

            if (!complaint.category ||
                !complaint.title ||
                !complaint.description) {
                alert("Please complete the category, title and description fields.");
                return;
            }

            if (submitBtn) {
                submitBtn.disabled = true;

                if (submitBtn.tagName === "INPUT") {
                    submitBtn.value = "Submitting...";
                } else {
                    submitBtn.textContent = "Submitting...";
                }
            }

            try {
                const result = await fetchJSON(
                    `${API_BASE_URL}/api/complaints`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(complaint)
                    }
                );

                alert(
                    `Complaint submitted successfully! Reference ID: ${result.id}`
                );

                complaintForm.reset();
                closeComplaintModal();
                await loadComplaints();

            } catch (error) {
                console.error("Complaint submission failed:", error);
                alert("Unable to submit complaint.\n\n" + error.message);

            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;

                    if (submitBtn.tagName === "INPUT") {
                        submitBtn.value = originalText;
                    } else {
                        submitBtn.textContent = originalText;
                    }
                }
            }
        });
    }

    // =========================================
    // RESET COMPLAINT FILTERS
    // =========================================

    document.getElementById("resetFilters")?.addEventListener("click", () => {
        if (statusFilter) statusFilter.value = "";
        if (categoryFilter) categoryFilter.value = "";
        applyComplaintFilters();
    });

    // =========================================
    // SIGN OUT
    // =========================================

    document.getElementById("signOutBtn")?.addEventListener("click", async event => {
        event.preventDefault();

        try {
            await fetchJSON(`${API_BASE_URL}/api/logout`, {
                method: "POST"
            });
        } catch (error) {
            console.error("Logout error:", error);
        }

        window.location.href = "login.html";
    });

    // =========================================
    // CLASSROOM FINDER
    // =========================================

    const classroomForm = document.getElementById("classroomSearchForm");
    const findClassroom = document.getElementById("findClassroom");
    const resultsBox = document.getElementById("classroomResults");
    const resultCount = document.getElementById("classroomResultCount");

    async function searchClassrooms(event) {
        event?.preventDefault();

        const dateValue = document.getElementById("date")?.value;
        const start = document.getElementById("time")?.value;

        if (!dateValue || !start) {
            alert("Please select a date and start time.");
            return;
        }

        const selectedDate = new Date(dateValue + "T12:00:00");
        const days = [
            "SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY",
            "THURSDAY", "FRIDAY", "SATURDAY"
        ];
        const day = days[selectedDate.getDay()];

        const [hours, minutes] = start.split(":").map(Number);
        const endMinutes = hours * 60 + minutes + 60;

        if (endMinutes > 24 * 60) {
            alert("Choose a start time that allows a full one-hour slot.");
            return;
        }

        const end = String(Math.floor(endMinutes / 60)).padStart(2, "0")
            + ":" + String(endMinutes % 60).padStart(2, "0");

        if (resultsBox) {
            resultsBox.innerHTML = "<p>Searching classroom availability...</p>";
        }
        if (resultCount) resultCount.textContent = "Searching...";

        if (findClassroom) {
            findClassroom.disabled = true;
            findClassroom.textContent = "Searching...";
        }

        try {
            const branch =
    document.getElementById("classroomBranch")?.value || "";

const division =
    document.getElementById("classroomDivision")?.value || "";
           
            const params = new URLSearchParams({
                day, start, end, branch, division
            });

            const data = await fetchJSON(
                `${API_BASE_URL}/api/classrooms/available?${params}`
            );

            const rooms = Array.isArray(data)
                ? data
                : data.classrooms || data.rooms || data.results || [];

            if (!resultsBox) return;

            if (!rooms.length) {
                resultsBox.innerHTML = `
                    <p>No classrooms available for the selected time.</p>
                    <p>Try another time slot.</p>`;
                if (resultCount) resultCount.textContent = "0 resources found";
                return;
            }

            
resultsBox.innerHTML = rooms.map(room => {
    const location = String(
        room.location || room.room_number || ""
    ).trim();

    // Skip records without a valid classroom name
    if (!location || location === "â€”" || location === "—") {
        return "";
    }

    return `
        <div class="classroom-card">
            <h3>${escapeHTML(location)}</h3>
            <p>Classroom Available</p>
        </div>
    `;
}).join("");

const displayedCount =
    resultsBox.querySelectorAll(".classroom-card").length;

if (displayedCount === 0) {
    resultsBox.innerHTML = `
        <p>No valid classroom names found for this time slot.</p>
        <p>Please verify the classroom records in the database.</p>
    `;
}

if (resultCount) {
    resultCount.textContent = `${displayedCount} classrooms found`;
}


            if (resultCount) {
                resultCount.textContent = `${rooms.length} resources found`;
            }

        } catch (error) {
            console.error("Classroom search error:", error);

            if (resultsBox) {
                resultsBox.innerHTML = `
                    <p>Could not load classroom availability.</p>
                    <p>${escapeHTML(error.message)}</p>`;
            }

            if (resultCount) resultCount.textContent = "Search failed";

        } finally {
            if (findClassroom) {
                findClassroom.disabled = false;
                findClassroom.textContent = "Find Classroom";
            }
        }
    }

    classroomForm?.addEventListener("submit", searchClassrooms);

    if (!classroomForm && findClassroom) {
        findClassroom.addEventListener("click", searchClassrooms);
    }

    // =========================================
    // TIMETABLE BRANCH / YEAR / DIVISION
    // =========================================

    const timetableBranch = document.getElementById("branch");
    const timetableYear = document.getElementById("year");
    const timetableDivision = document.getElementById("division");

    const timetableDivisions = {
        INFT: { FE: ["A", "B"], SE: ["A", "B"], TE: ["A", "B"], BE: ["A", "B"] },
        CMPN: { FE: ["A", "B"], SE: ["A", "B"], TE: ["A", "B"], BE: ["A", "B"] },
        EXTC: { FE: ["A", "B"], SE: ["A", "B"], TE: ["A", "B"], BE: ["A", "B"] },
        EXCS: { FE: ["A", "B"], SE: ["A", "B"], TE: ["A", "B"], BE: ["A", "B"] },
        BIOMED: { FE: ["A", "B"], SE: ["A", "B"], TE: ["A", "B"], BE: ["A", "B"] }
    };

    function updateTimetableDivisions() {
        if (!timetableDivision) return;

        const branch = timetableBranch?.value || "";
        const year = timetableYear?.value || "";

        timetableDivision.innerHTML =
            '<option value="">Select division</option>';

        (timetableDivisions[branch]?.[year] || []).forEach(division => {
            const option = document.createElement("option");
            option.value = division;
            option.textContent = division;
            timetableDivision.appendChild(option);
        });
    }

    timetableBranch?.addEventListener("change", updateTimetableDivisions);
    timetableYear?.addEventListener("change", updateTimetableDivisions);

    // =========================================
    // TIMETABLE VIEWER
    // =========================================

    const viewTimetable = document.getElementById("viewTimetable");
    const resetTimetable = document.getElementById("resetTimetable");

    viewTimetable?.addEventListener("click", async () => {
        const branch = timetableBranch?.value || "";
        const year = timetableYear?.value || "";
        const division = timetableDivision?.value || "";
        const day = document.getElementById("day")?.value || "";
        const view = document.getElementById("view")?.value || "weekly";
        const timetableCard = document.querySelector(".timetable-card");

        if (!branch || !year || !division) {
            alert("Please select branch, year and division.");
            return;
        }

        if (!timetableCard) {
            alert("Timetable display section was not found.");
            return;
        }

        timetableCard.innerHTML = "<p>Loading timetable...</p>";

        try {
            const params = new URLSearchParams({ branch, division });

            if (view === "daily" && day) {
                params.set("day", day.toUpperCase());
            }

            const data = await fetchJSON(
                `${API_BASE_URL}/api/timetable?${params}`
            );

            const rows = (data.results || []).filter(item =>
                String(item.year_level || "").toUpperCase() === year.toUpperCase()
            );

            if (!rows.length) {
                timetableCard.innerHTML =
                    "<p>No timetable records found for this selection.</p>";
                return;
            }

            const dayOrder = [
                "MONDAY", "TUESDAY", "WEDNESDAY",
                "THURSDAY", "FRIDAY", "SATURDAY"
            ];

            const grouped = {};

            rows.forEach(item => {
                const dayName = String(item.day || "OTHER").toUpperCase();
                if (!grouped[dayName]) grouped[dayName] = [];
                grouped[dayName].push(item);
            });

            const daysToShow = view === "daily" && day
                ? [day.toUpperCase()]
                : dayOrder;

            let html = "";

            daysToShow.forEach(dayName => {
                const lessons = (grouped[dayName] || []).sort((a, b) =>
                    String(a.time_slot || "").localeCompare(String(b.time_slot || ""))
                );

                if (!lessons.length) return;

                html += `
                    <div class="timetable-day">
                        <h3>${escapeHTML(dayName)}</h3>
                        <div class="timetable-table-wrap">
                            <table class="timetable-table">
                                <thead>
                                    <tr>
                                        <th>Time</th>
                                        <th>Subject</th>
                                        <th>Professor</th>
                                        <th>Room</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${lessons.map(item => `
                                        <tr>
                                            <td>${escapeHTML(item.time_slot || "—")}</td>
                                            <td>${escapeHTML(item.subject_code || "—")}</td>
                                            <td>${escapeHTML(item.prof_code || "—")}</td>
                                            <td>${escapeHTML(item.location || "Not Assigned")}</td>
                                        </tr>
                                    `).join("")}
                                </tbody>
                            </table>
                        </div>
                    </div>`;
            });

            timetableCard.innerHTML = html ||
                "<p>No timetable records found for this selection.</p>";

        } catch (error) {
            console.error("Timetable error:", error);
            timetableCard.innerHTML = `
                <p>Could not load timetable.</p>
                <p>${escapeHTML(error.message)}</p>`;
        }
    });

    resetTimetable?.addEventListener("click", () => {
        if (timetableBranch) timetableBranch.value = "";
        if (timetableYear) timetableYear.value = "";

        if (timetableDivision) {
            timetableDivision.innerHTML =
                '<option value="">Select division</option>';
        }

        const daySelect = document.getElementById("day");
        if (daySelect) daySelect.value = "";

        const viewSelect = document.getElementById("view");
        if (viewSelect) viewSelect.value = "weekly";

        const timetableCard = document.querySelector(".timetable-card");

        if (timetableCard) {
            timetableCard.innerHTML = `
                <div class="empty-timetable">
                    <p>Select branch, year and division to view the timetable.</p>
                </div>`;
        }
    });

    // =========================================
    // INITIALIZE PAGE
    // =========================================

    // Initialize session role first, then load the appropriate complaints.
    (async () => {
        const authenticated = await initializeUserRole();
        if (!authenticated) return;

        if (
            document.getElementById("complaintsList") ||
            document.getElementById("complaintForm")
        ) {
            await loadComplaints();
        }
    })();
});
