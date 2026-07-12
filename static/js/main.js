// BuildSense Client Controller

document.addEventListener("DOMContentLoaded", () => {
    // State management
    let state = {
        imagePath: "",
        fileUrl: "",
        spatialData: null,
        isConfigured: false,
        activePreset: false
    };

    // DOM Elements
    const elements = {
        uploadDropzone: document.getElementById("uploadDropzone"),
        fileInput: document.getElementById("fileInput"),
        loadDemoBtn: document.getElementById("loadDemoBtn"),
        canvasContainer: document.getElementById("canvasContainer"),
        canvasControls: document.getElementById("canvasControls"),
        lblTotalArea: document.getElementById("lblTotalArea"),
        lblCorridors: document.getElementById("lblCorridors"),
        lblExits: document.getElementById("lblExits"),
        blueprintCanvas: document.getElementById("blueprintCanvas"),
        canvasTooltip: document.getElementById("canvasTooltip"),
        
        // Orchestrator Nodes
        graphConnections: document.getElementById("graphConnections"),
        nodeCoordinator: document.getElementById("node-coordinator"),
        nodeBlueprint: document.getElementById("node-blueprint"),
        nodeCost: document.getElementById("node-cost"),
        nodeCompliance: document.getElementById("node-compliance"),
        nodeScheduling: document.getElementById("node-scheduling"),
        nodeWorkforce: document.getElementById("node-workforce"),
        orchestratorStatus: document.getElementById("orchestratorStatus"),
        
        // Chat Section
        chatHistory: document.getElementById("chatHistory"),
        chatInput: document.getElementById("chatInput"),
        sendBtn: document.getElementById("sendBtn"),
        clearChatBtn: document.getElementById("clearChatBtn"),
        presetQueryBtn: document.getElementById("presetQueryBtn"),
        
        // Settings Modal
        engineModeBadge: document.getElementById("engineModeBadge"),
        openSettingsBtn: document.getElementById("openSettingsBtn"),
        settingsModal: document.getElementById("settingsModal"),
        closeSettingsBtn: document.getElementById("closeSettingsBtn"),
        cancelSettingsBtn: document.getElementById("cancelSettingsBtn"),
        saveSettingsBtn: document.getElementById("saveSettingsBtn"),
        apiKeyInput: document.getElementById("apiKeyInput"),
        toggleKeyVisibility: document.getElementById("toggleKeyVisibility"),
        modalStatusBox: document.getElementById("modalStatusBox")
    };

    // Canvas drawing context
    const ctx = elements.blueprintCanvas.getContext("2d");
    let bgImage = new Image();

    // ----------------------------------------------------
    // SVG Connection Drawing
    // ----------------------------------------------------
    function drawConnectionPaths() {
        const rectGraph = document.querySelector(".orchestrator-graph").getBoundingClientRect();
        
        const getCenter = (element) => {
            const rect = element.getBoundingClientRect();
            return {
                x: rect.left - rectGraph.left + rect.width / 2,
                y: rect.top - rectGraph.top + rect.height / 2
            };
        };

        const coord = getCenter(elements.nodeCoordinator);
        const blueprint = getCenter(elements.nodeBlueprint);
        const cost = getCenter(elements.nodeCost);
        const compliance = getCenter(elements.nodeCompliance);
        const scheduling = getCenter(elements.nodeScheduling);
        const workforce = getCenter(elements.nodeWorkforce);

        const setPathSCurve = (pathId, p1, p2) => {
            const path = document.getElementById(pathId);
            if (!path) return;
            // Draw S-curve (Cubic Bezier)
            const dx = p2.x - p1.x;
            const controlX1 = p1.x + dx * 0.4;
            const controlX2 = p1.x + dx * 0.6;
            const d = `M ${p1.x} ${p1.y} C ${controlX1} ${p1.y}, ${controlX2} ${p2.y}, ${p2.x} ${p2.y}`;
            path.setAttribute("d", d);
        };

        setPathSCurve("path-blueprint", coord, blueprint);
        setPathSCurve("path-cost", coord, cost);
        setPathSCurve("path-compliance", coord, compliance);
        setPathSCurve("path-scheduling", coord, scheduling);
        setPathSCurve("path-workforce", coord, workforce);
    }

    // Adjust SVG sizes and draw paths on resize
    window.addEventListener("resize", drawConnectionPaths);
    // Trigger initial drawing after layout settles
    setTimeout(drawConnectionPaths, 500);

    // ----------------------------------------------------
    // Engine Configurations (API Key Settings)
    // ----------------------------------------------------
    async function checkEngineStatus() {
        try {
            const res = await fetch("/api/config");
            const data = await res.json();
            state.isConfigured = data.is_configured;
            
            const badgeText = elements.engineModeBadge.querySelector(".mode-text");
            const badgeDot = elements.engineModeBadge.querySelector(".status-dot");
            
            if (state.isConfigured) {
                badgeText.textContent = "Live Mode";
                badgeDot.className = "status-dot live";
                elements.apiKeyInput.value = "••••••••••••••••••••••••";
            } else {
                badgeText.textContent = "Simulation Mode";
                badgeDot.className = "status-dot pulsing";
                elements.apiKeyInput.value = "";
            }
        } catch (e) {
            console.error("Failed to query API config:", e);
        }
    }
    checkEngineStatus();

    // Modal Events
    elements.openSettingsBtn.addEventListener("click", () => {
        elements.settingsModal.classList.add("active");
        updateModalStatus();
    });

    const closeModal = () => elements.settingsModal.classList.remove("active");
    elements.closeSettingsBtn.addEventListener("click", closeModal);
    elements.cancelSettingsBtn.addEventListener("click", closeModal);
    
    // Toggle key show/hide
    elements.toggleKeyVisibility.addEventListener("click", () => {
        const type = elements.apiKeyInput.type === "password" ? "text" : "password";
        elements.apiKeyInput.type = type;
        const icon = elements.toggleKeyVisibility.querySelector("i");
        icon.className = type === "password" ? "fa-solid fa-eye" : "fa-solid fa-eye-slash";
    });

    function updateModalStatus() {
        const box = elements.modalStatusBox;
        const dot = box.querySelector(".status-dot");
        const txt = box.querySelector(".status-text");
        
        if (state.isConfigured) {
            dot.className = "status-dot live";
            txt.textContent = "Live Mode Enabled (Connected to Gemini API)";
        } else {
            dot.className = "status-dot pulsing";
            txt.textContent = "Simulation Mode Active (Using built-in scenarios)";
        }
    }

    elements.saveSettingsBtn.addEventListener("click", async () => {
        const apiKey = elements.apiKeyInput.value.trim();
        // Avoid sending bullets if no changes made
        const finalKey = apiKey.includes("••") ? null : apiKey;
        
        if (finalKey !== null) {
            try {
                const res = await fetch("/api/config", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ api_key: finalKey })
                });
                const data = await res.json();
                state.isConfigured = data.is_configured;
            } catch (e) {
                alert("Failed to update API key: " + e.message);
            }
        }
        
        await checkEngineStatus();
        updateModalStatus();
        closeModal();
    });

    // ----------------------------------------------------
    // Floor Plan Blueprint Visualizer (Canvas Rendering)
    // ----------------------------------------------------
    function renderBlueprint() {
        if (!state.spatialData) return;
        
        const canvas = elements.blueprintCanvas;
        const wrapper = canvas.parentElement;
        
        // Scale canvas to image dimensions or parent container
        const imgWidth = bgImage.naturalWidth || 800;
        const imgHeight = bgImage.naturalHeight || 600;
        
        canvas.width = imgWidth;
        canvas.height = imgHeight;
        
        // Draw background image
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(bgImage, 0, 0, canvas.width, canvas.height);
        
        // Draw overlays
        // 1. Corridors (orange)
        (state.spatialData.corridors || []).forEach(corr => {
            const [rx, ry, rw, rh] = corr.coords;
            const x = (rx / 100) * canvas.width;
            const y = (ry / 100) * canvas.height;
            const w = (rw / 100) * canvas.width;
            const h = (rh / 100) * canvas.height;
            
            ctx.fillStyle = "rgba(255, 170, 0, 0.22)";
            ctx.strokeStyle = "rgba(255, 170, 0, 0.85)";
            ctx.lineWidth = 2.5;
            ctx.fillRect(x, y, w, h);
            ctx.strokeRect(x, y, w, h);
            
            // Corridor label
            ctx.fillStyle = "#ffaa00";
            ctx.font = "bold 11px Outfit";
            ctx.fillText(corr.name, x + 6, y + 16);
        });

        // 2. Rooms (blue)
        (state.spatialData.rooms || []).forEach(room => {
            const [rx, ry, rw, rh] = room.coords;
            const x = (rx / 100) * canvas.width;
            const y = (ry / 100) * canvas.height;
            const w = (rw / 100) * canvas.width;
            const h = (rh / 100) * canvas.height;
            
            ctx.fillStyle = "rgba(0, 210, 255, 0.15)";
            ctx.strokeStyle = "rgba(0, 210, 255, 0.85)";
            ctx.lineWidth = 2;
            ctx.fillRect(x, y, w, h);
            ctx.strokeRect(x, y, w, h);
            
            // Room label
            ctx.fillStyle = "#00d2ff";
            ctx.font = "bold 11px Outfit";
            ctx.fillText(room.name, x + 6, y + 16);
        });

        // 3. Exits (green)
        (state.spatialData.exits || []).forEach(ex => {
            const [rx, ry, rw, rh] = ex.coords;
            const x = (rx / 100) * canvas.width;
            const y = (ry / 100) * canvas.height;
            const w = (rw / 100) * canvas.width;
            const h = (rh / 100) * canvas.height;
            
            ctx.fillStyle = "rgba(0, 255, 170, 0.25)";
            ctx.strokeStyle = "rgba(0, 255, 170, 0.9)";
            ctx.lineWidth = 3;
            ctx.fillRect(x, y, w, h);
            ctx.strokeRect(x, y, w, h);
        });
    }

    // Mouse hover listener on Canvas for tooltips
    elements.blueprintCanvas.addEventListener("mousemove", (e) => {
        if (!state.spatialData) return;
        
        const canvas = elements.blueprintCanvas;
        const rect = canvas.getBoundingClientRect();
        
        // Calculate coordinate percentages
        const clickX = ((e.clientX - rect.left) / rect.width) * 100;
        const clickY = ((e.clientY - rect.top) / rect.height) * 100;
        
        let hoveredItem = null;
        let itemType = "";

        // Check Rooms
        (state.spatialData.rooms || []).forEach(room => {
            const [rx, ry, rw, rh] = room.coords;
            if (clickX >= rx && clickX <= rx + rw && clickY >= ry && clickY <= ry + rh) {
                hoveredItem = room;
                itemType = "room";
            }
        });

        // Check Corridors
        if (!hoveredItem) {
            (state.spatialData.corridors || []).forEach(corr => {
                const [rx, ry, rw, rh] = corr.coords;
                if (clickX >= rx && clickX <= rx + rw && clickY >= ry && clickY <= ry + rh) {
                    hoveredItem = corr;
                    itemType = "corridor";
                }
            });
        }

        // Check Exits
        if (!hoveredItem) {
            (state.spatialData.exits || []).forEach(ex => {
                const [rx, ry, rw, rh] = ex.coords;
                if (clickX >= rx && clickX <= rx + rw && clickY >= ry && clickY <= ry + rh) {
                    hoveredItem = ex;
                    itemType = "exit";
                }
            });
        }

        const tooltip = elements.canvasTooltip;
        if (hoveredItem) {
            // Show Tooltip
            tooltip.style.display = "block";
            tooltip.style.left = `${e.clientX - rect.left + 15}px`;
            tooltip.style.top = `${e.clientY - rect.top + 15}px`;
            
            if (itemType === "room") {
                tooltip.innerHTML = `
                    <h4><i class="fa-solid fa-cube"></i> ${hoveredItem.name}</h4>
                    <p><strong>Dimensions:</strong> ${hoveredItem.dimensions}</p>
                    <p><strong>Area:</strong> ${hoveredItem.area_sqft} sq ft</p>
                `;
            } else if (itemType === "corridor") {
                tooltip.innerHTML = `
                    <h4><i class="fa-solid fa-route"></i> ${hoveredItem.name}</h4>
                    <p><strong>Width:</strong> ${hoveredItem.width_m} meters</p>
                    <p><strong>Length:</strong> ${hoveredItem.length_m} meters</p>
                `;
            } else if (itemType === "exit") {
                tooltip.innerHTML = `
                    <h4><i class="fa-solid fa-door-open"></i> ${hoveredItem.name}</h4>
                    <p><strong>Type:</strong> ${hoveredItem.type.replace("_", " ")}</p>
                `;
            }
        } else {
            tooltip.style.display = "none";
        }
    });

    elements.blueprintCanvas.addEventListener("mouseleave", () => {
        elements.canvasTooltip.style.display = "none";
    });

    // ----------------------------------------------------
    // Uploader Logic
    // ----------------------------------------------------
    async function handleBlueprintData(data) {
        state.imagePath = data.image_path;
        state.fileUrl = data.file_url;
        state.spatialData = data.spatial_data;

        // Render controls details
        elements.lblTotalArea.innerHTML = `<i class="fa-solid fa-ruler-combined"></i> ${state.spatialData.total_area_sqft.toLocaleString()} sq ft`;
        elements.lblCorridors.innerHTML = `<i class="fa-solid fa-route"></i> ${state.spatialData.corridors.length} Corridor(s)`;
        elements.lblExits.innerHTML = `<i class="fa-solid fa-door-open"></i> ${state.spatialData.exits.length} Exit(s)`;
        
        elements.uploadDropzone.style.display = "none";
        elements.canvasContainer.style.display = "flex";
        elements.canvasControls.style.display = "flex";

        // Load background image
        bgImage.src = state.fileUrl;
        bgImage.onload = () => {
            renderBlueprint();
            drawConnectionPaths();
        };

        // Add a message in chat indicating blueprint ingested
        addChatMessage("system", `
            <h3>Blueprint Ingested Successfully</h3>
            <p><strong>Total Area:</strong> ${state.spatialData.total_area_sqft} sq ft</p>
            <p><strong>Structure:</strong> Extracted ${state.spatialData.rooms.length} rooms and ${state.spatialData.corridors.length} main corridor pathway.</p>
            <p>${state.spatialData.raw_analysis}</p>
        `);
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);
        
        addChatMessage("system", "<p><i class='fa-solid fa-spinner fa-spin'></i> Uploading drawing and initiating Blueprint Vision Analysis Agent...</p>");
        
        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (data.error) {
                addChatMessage("system", `<p class="text-danger"><i class="fa-solid fa-circle-exclamation"></i> Error: ${data.error}</p>`);
            } else {
                handleBlueprintData(data);
            }
        } catch (e) {
            addChatMessage("system", `<p class="text-danger"><i class="fa-solid fa-circle-exclamation"></i> Upload Failed: ${e.message}</p>`);
        }
    }

    // Drag-and-drop events
    elements.uploadDropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        elements.uploadDropzone.style.borderColor = "var(--color-blue)";
        elements.uploadDropzone.style.backgroundColor = "rgba(0, 210, 255, 0.05)";
    });

    elements.uploadDropzone.addEventListener("dragleave", () => {
        elements.uploadDropzone.style.borderColor = "var(--border-glass)";
        elements.uploadDropzone.style.backgroundColor = "transparent";
    });

    elements.uploadDropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        elements.uploadDropzone.style.borderColor = "var(--border-glass)";
        elements.uploadDropzone.style.backgroundColor = "transparent";
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });

    elements.fileInput.addEventListener("change", (e) => {
        const files = e.target.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });

    // Preset Demo
    elements.loadDemoBtn.addEventListener("click", (e) => {
        e.stopPropagation(); // Avoid triggering file input click
        loadDemoBlueprint();
    });

    async function loadDemoBlueprint() {
        addChatMessage("system", "<p><i class='fa-solid fa-spinner fa-spin'></i> Sourcing blueprint demo and running Blueprint Analysis Agent...</p>");
        try {
            // Triggering query empty upload gets standard mock layout image
            const res = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: "analyze layout schema", budget_limit: 1500000 })
            });
            const data = await res.json();
            
            // Generate mock file details
            const mockUploadData = {
                image_path: "",
                file_url: "/uploads/mock_blueprint.png",
                spatial_data: data.spatial_data
            };
            handleBlueprintData(mockUploadData);
        } catch (e) {
            addChatMessage("system", `<p class="text-danger"><i class="fa-solid fa-circle-exclamation"></i> Demo Load Failed: ${e.message}</p>`);
        }
    }

    // ----------------------------------------------------
    // Multi-Agent Map Animations
    // ----------------------------------------------------
    function animatePipeline(routingPlan, callback) {
        let step = 0;
        elements.orchestratorStatus.textContent = "Coordinator routing tasks...";
        elements.orchestratorStatus.style.color = "var(--color-orange)";
        
        // Reset nodes classes
        document.querySelectorAll(".agent-node").forEach(n => {
            if (n.id !== "node-coordinator") n.className = "agent-node node-specialist";
        });
        document.querySelectorAll(".conn-path").forEach(p => p.className.baseVal = "conn-path");
        
        elements.nodeCoordinator.className = "agent-node node-coordinator processing";
        elements.nodeCoordinator.querySelector(".node-status").textContent = "Routing...";

        const steps = [
            { node: elements.nodeBlueprint, path: "path-blueprint", status: "Vision Checking..." },
            { node: elements.nodeCost, path: "path-cost", status: "Calculating BOQ..." },
            { node: elements.nodeCompliance, path: "path-compliance", status: "Checking Code..." },
            { node: elements.nodeScheduling, path: "path-scheduling", status: "Scheduling..." },
            { node: elements.nodeWorkforce, path: "path-workforce", status: "Matching Trades..." }
        ];

        // Process step-by-step to show the parallel routing
        function nextStep() {
            if (step >= steps.length) {
                // Done routing, now synthesis
                elements.orchestratorStatus.textContent = "Coordinator synthesizing...";
                elements.nodeCoordinator.querySelector(".node-status").textContent = "Synthesizing...";
                
                setTimeout(() => {
                    elements.orchestratorStatus.textContent = "Ready";
                    elements.orchestratorStatus.style.color = "var(--text-secondary)";
                    elements.nodeCoordinator.className = "agent-node node-coordinator active";
                    elements.nodeCoordinator.querySelector(".node-status").textContent = "Ready";
                    
                    // Mark all active connections completed
                    document.querySelectorAll(".conn-path").forEach(p => {
                        if (p.classList.contains("active")) {
                            p.classList.remove("active");
                            p.classList.add("completed");
                        }
                    });
                    
                    if (callback) callback();
                }, 1000);
                return;
            }

            const current = steps[step];
            // Activate line
            const pathElement = document.getElementById(current.path);
            pathElement.classList.add("active");
            
            // Activate node processing
            current.node.className = "agent-node node-specialist processing";
            current.node.querySelector(".node-status").textContent = "Working...";

            setTimeout(() => {
                // Done processing
                // Check if compliance failed or has conflict to mark node warning
                let hasConflict = false;
                if (current.node.id === "node-compliance" && state.spatialData && state.spatialData.corridors[0].width_m < 1.2) {
                    hasConflict = true;
                }
                if (current.node.id === "node-workforce" && state.activePreset) {
                    hasConflict = true;
                }

                if (hasConflict) {
                    current.node.className = "agent-node node-specialist warning";
                    current.node.querySelector(".node-status").textContent = "Alert!";
                } else {
                    current.node.className = "agent-node node-specialist success";
                    current.node.querySelector(".node-status").textContent = "Complete";
                }
                
                step++;
                nextStep();
            }, 600);
        }

        setTimeout(nextStep, 500);
    }

    // ----------------------------------------------------
    // Chat System & API Queries
    // ----------------------------------------------------
    function addChatMessage(sender, contentHTML) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `chat-message ${sender === "user" ? "user-message" : "system-message"}`;
        
        const icon = sender === "user" ? "fa-user" : "fa-robot";
        
        messageDiv.innerHTML = `
            <div class="msg-icon"><i class="fa-solid ${icon}"></i></div>
            <div class="msg-content">${contentHTML}</div>
        `;
        
        elements.chatHistory.appendChild(messageDiv);
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
    }

    function addLoadingMessage() {
        const messageDiv = document.createElement("div");
        messageDiv.className = "chat-message system-message loading-placeholder";
        messageDiv.innerHTML = `
            <div class="msg-icon"><i class="fa-solid fa-spinner fa-spin"></i></div>
            <div class="msg-content">
                <p>Orchestrating agents... Coordinator Dispatcher running...</p>
            </div>
        `;
        elements.chatHistory.appendChild(messageDiv);
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
        return messageDiv;
    }

    async function sendQuery(queryText) {
        if (!queryText.trim()) return;
        
        // If query is target preset, flag workforce warning simulation
        if (queryText.includes("15 lakh") || queryText.includes("15L")) {
            state.activePreset = true;
        } else {
            state.activePreset = false;
        }

        addChatMessage("user", `<p>${queryText}</p>`);
        elements.chatInput.value = "";
        
        // Show loading bubble
        const loadingBubble = addLoadingMessage();

        // 1. Run Map Animation first, then call backend
        animatePipeline([], async () => {
            try {
                const res = await fetch("/api/query", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        query: queryText,
                        image_path: state.imagePath,
                        budget_limit: 1500000 // default budget context
                    })
                });
                
                const data = await res.json();
                
                // Remove loading bubble
                if (loadingBubble && loadingBubble.parentNode) {
                    loadingBubble.parentNode.removeChild(loadingBubble);
                }
                
                if (data.error) {
                    addChatMessage("system", `<p class="text-danger"><i class="fa-solid fa-circle-exclamation"></i> Execution Error: ${data.error}</p>`);
                    return;
                }

                // Append Coordinator Synthesis Markdown
                // Convert simple Markdown text to HTML structure
                const formattedRec = formatMarkdown(data.synthesized_recommendation);
                addChatMessage("system", `
                    <div class="recommendation-synthesis">
                        ${formattedRec}
                    </div>
                `);

                // Append Collapsible cards for each specialist output
                appendSpecialistCards(data.specialist_outputs);

            } catch (e) {
                if (loadingBubble && loadingBubble.parentNode) {
                    loadingBubble.parentNode.removeChild(loadingBubble);
                }
                addChatMessage("system", `<p class="text-danger"><i class="fa-solid fa-circle-exclamation"></i> Network Error: ${e.message}</p>`);
            }
        });
    }

    // Helper to format Markdown from LLM response
    function formatMarkdown(md) {
        if (!md) return "";
        let html = md;
        
        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        
        // Strong
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Horizontal lines
        html = html.replace(/^\s*---\s*$/gim, '<hr class="md-divider">');
        
        // Bullet Lists
        html = html.replace(/^\s*\*\s+(.*$)/gim, '<li>$1</li>');
        html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
        // Wrap adjacent li in ul
        // A simple parser for lists:
        const lines = html.split('\n');
        let inList = false;
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].startsWith('<li>')) {
                if (!inList) {
                    lines[i] = '<ul>' + lines[i];
                    inList = true;
                }
            } else {
                if (inList) {
                    lines[i-1] = lines[i-1] + '</ul>';
                    inList = false;
                }
            }
        }
        if (inList) lines[lines.length - 1] += '</ul>';
        html = lines.join('\n');
        
        // Paragraphs (wrap blocks of text without html tags)
        html = html.split('\n\n').map(block => {
            const trimmed = block.trim();
            if (!trimmed) return "";
            if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<li') || trimmed.startsWith('<hr')) {
                return trimmed;
            }
            return `<p>${trimmed.replace(/\n/g, "<br>")}</p>`;
        }).join('\n');

        return html;
    }

    function appendSpecialistCards(outputs) {
        if (!outputs) return;
        
        const cardContainer = document.createElement("div");
        cardContainer.className = "specialist-cards-row";
        
        // 1. Cost estimation card
        if (outputs.cost_estimation) {
            const cost = outputs.cost_estimation;
            let boqRows = cost.boq.map(item => `
                <tr>
                    <td>${item.item}</td>
                    <td>${item.quantity}</td>
                    <td>${item.cost_inr ? `₹${(item.cost_inr/100000).toFixed(2)}L` : item.rate}</td>
                </tr>
            `).join("");
            
            createActivityCard(
                "Calculator", 
                "Cost Estimation Agent BOQ", 
                `
                <table class="boq-table">
                    <thead>
                        <tr>
                            <th>Item Category</th>
                            <th>Quantity</th>
                            <th>Cost (INR)</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${boqRows}
                        <tr>
                            <td><strong>Total Estimate</strong></td>
                            <td>-</td>
                            <td><strong>${cost.formatted_total_cost}</strong></td>
                        </tr>
                    </tbody>
                </table>
                <p style="margin-top: 8px; font-size:11px; color:var(--text-secondary);">${cost.cost_explanation}</p>
                `
            );
        }

        // 2. Compliance checks card
        if (outputs.code_compliance) {
            const comp = outputs.code_compliance;
            let checkItems = comp.compliance_checks.map(item => {
                const iconClass = item.status === "PASS" ? "pass fa-check-circle" : (item.status === "FAIL" ? "fail fa-times-circle" : "warning fa-exclamation-triangle");
                return `
                    <div class="checklist-item">
                        <i class="fa-solid ${iconClass} check-icon"></i>
                        <div class="check-details">
                            <span class="check-title">${item.rule} [${item.status}]</span>
                            <span class="check-message">${item.message}</span>
                            <span class="check-citation">${item.nbc_citation}</span>
                        </div>
                    </div>
                `;
            }).join("");
            
            createActivityCard(
                "Scale", 
                "Code Compliance Agent Checks", 
                `
                <div class="compliance-checklist">
                    ${checkItems}
                </div>
                `
            );
        }

        // 3. Scheduling card
        if (outputs.scheduling) {
            const sched = outputs.scheduling;
            let timelineItems = sched.timeline.map(phase => `
                <div class="timeline-item">
                    <div class="timeline-dot"></div>
                    <div class="timeline-details">
                        <span class="timeline-phase">${phase.phase}</span>
                        <span class="timeline-days">${phase.duration_days} days &bull; Milestone: ${phase.milestone}</span>
                    </div>
                </div>
            `).join("");
            
            createActivityCard(
                "Calendar", 
                "Scheduling Agent Timeline", 
                `
                <div class="scheduling-timeline" style="margin-bottom:8px;">
                    ${timelineItems}
                </div>
                <p style="font-size:11px; color:var(--text-secondary);"><strong>Total Duration:</strong> ${sched.total_duration_days} Days</p>
                `
            );
        }

        // 4. Workforce matching card
        if (outputs.workforce) {
            const wf = outputs.workforce;
            let wfItems = wf.matches.map(match => {
                const statusClass = match.status === "Available" ? "text-success" : "text-danger";
                return `
                    <div class="workforce-item">
                        <div>
                            <span class="wf-contractor">${match.matched_contractor}</span>
                            <br><span style="font-size:10px; color:var(--text-muted);">${match.trade_category}</span>
                        </div>
                        <div style="text-align:right;">
                            <span class="wf-rate">₹${match.daily_rate_inr}/day</span>
                            <br><span class="wf-status ${statusClass}" style="font-size:10px; font-weight:600;">${match.status}</span>
                        </div>
                    </div>
                    ${match.conflict_details ? `<p style="font-size:10.5px; color:var(--color-orange); margin-top:2px; margin-bottom:6px;">&bull; ${match.conflict_details}</p>` : ''}
                    <hr style="border:none; border-bottom:1px solid rgba(255,255,255,0.03); margin:4px 0;">
                `;
            }).join("");
            
            createActivityCard(
                "PeopleGroup", 
                "Workforce Agent Matches", 
                `
                <div class="workforce-list">
                    ${wfItems}
                </div>
                `
            );
        }
    }

    function createActivityCard(iconName, agentTitle, bodyHTML) {
        const cardDiv = document.createElement("div");
        cardDiv.className = "agent-activity-card";
        
        let faIcon = "fa-cogs";
        if (iconName === "Calculator") faIcon = "fa-calculator";
        if (iconName === "Scale") faIcon = "fa-scale-balanced";
        if (iconName === "Calendar") faIcon = "fa-calendar-days";
        if (iconName === "PeopleGroup") faIcon = "fa-people-group";
        
        cardDiv.innerHTML = `
            <div class="activity-header">
                <span><i class="fa-solid ${faIcon}" style="color:var(--color-orange); margin-right:6px;"></i> ${agentTitle}</span>
                <i class="fa-solid fa-chevron-down toggle-arrow"></i>
            </div>
            <div class="activity-body">
                ${bodyHTML}
            </div>
        `;
        
        // Collapsible binding
        const header = cardDiv.querySelector(".activity-header");
        const body = cardDiv.querySelector(".activity-body");
        const arrow = cardDiv.querySelector(".toggle-arrow");
        
        header.addEventListener("click", () => {
            body.classList.toggle("collapsed");
            header.classList.toggle("collapsed");
            if (body.classList.contains("collapsed")) {
                arrow.style.transform = "rotate(-90deg)";
            } else {
                arrow.style.transform = "rotate(0deg)";
            }
        });
        
        elements.chatHistory.appendChild(cardDiv);
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
    }

    // Input area handlers
    elements.sendBtn.addEventListener("click", () => {
        const text = elements.chatInput.value.trim();
        sendQuery(text);
    });

    elements.chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const text = elements.chatInput.value.trim();
            sendQuery(text);
        }
    });

    elements.presetQueryBtn.addEventListener("click", () => {
        // Load demo blueprint first if none loaded
        if (!state.spatialData) {
            loadDemoBlueprint().then(() => {
                sendQuery("Can we finish Phase 2 within a ₹15 lakh budget while staying compliant with fire safety norms?");
            });
        } else {
            sendQuery("Can we finish Phase 2 within a ₹15 lakh budget while staying compliant with fire safety norms?");
        }
    });

    elements.clearChatBtn.addEventListener("click", () => {
        // Clear chat items keep welcome
        const welcome = elements.chatHistory.querySelector(".system-message");
        elements.chatHistory.innerHTML = "";
        if (welcome) elements.chatHistory.appendChild(welcome);
        
        // Reset node visuals
        document.querySelectorAll(".agent-node").forEach(n => {
            if (n.id !== "node-coordinator") n.className = "agent-node node-specialist";
        });
        document.querySelectorAll(".conn-path").forEach(p => p.className.baseVal = "conn-path");
    });
});
