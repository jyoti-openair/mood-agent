document.addEventListener("DOMContentLoaded", () => {
  // Aligned directly with moods.py catalog
  const MOODS = [
    { id: "anxious", label: "Anxious", emoji: "🌀", color: "#FF6B35" },
    { id: "angry", label: "Angry", emoji: "🔥", color: "#E93CAC" },
    { id: "sad", label: "Sad", emoji: "🌧️", color: "#5B6EE1" },
    { id: "lost", label: "Lost / Confused", emoji: "🧭", color: "#9B5DE5" },
    { id: "jealous", label: "Jealous", emoji: "💚", color: "#2EC4B6" },
    { id: "guilty", label: "Guilty", emoji: "⚖️", color: "#FFD23F" },
    { id: "stuck", label: "Stuck", emoji: "🪨", color: "#8D5A2B" },
    { id: "lonely", label: "Lonely", emoji: "🌙", color: "#3A86FF" },
    { id: "overwhelmed", label: "Overwhelmed", emoji: "🌊", color: "#FB5607" },
    { id: "joyful", label: "Joyful", emoji: "✨", color: "#FFBE0B" }
  ];

  // DOM Elements
  const mandalaContainer = document.getElementById("mandala");
  const loadingSection = document.getElementById("loading-section");
  const responseSection = document.getElementById("response-section");
  const errorSection = document.getElementById("error-section");
  const responseKicker = document.getElementById("response-kicker");
  const responseBody = document.getElementById("response-body");
  const responseMeta = document.getElementById("response-meta");
  const errorText = document.getElementById("error-text");
  const againBtn = document.getElementById("again-btn");

  // Render Interactive Circular Mood Nodes
  function renderMandala() {
    if (!mandalaContainer) return;

    mandalaContainer.innerHTML = "";
    MOODS.forEach((mood) => {
      const node = document.createElement("button");
      node.className = "mandala-node";
      node.type = "button";
      node.setAttribute("role", "option");
      node.setAttribute("aria-selected", "false");
      
      // Inject custom inline style to power dynamic color glows
      node.style.setProperty("--mood-color", mood.color);

      node.innerHTML = `
        <div class="mandala-circle" style="background-color: ${mood.color}15; border-color: ${mood.color};">
          <span class="mandala-emoji" role="img" aria-label="${mood.label}">${mood.emoji}</span>
        </div>
        <span class="mandala-node__label">${mood.label}</span>
      `;

      node.addEventListener("click", () => handleMoodSelect(mood));
      mandalaContainer.appendChild(node);
    });
  }

  // Handle Selection & Post to Backend
  async function handleMoodSelect(mood) {
    if (mandalaContainer.parentElement) {
      mandalaContainer.parentElement.classList.add("hidden");
    }
    loadingSection.classList.remove("hidden");
    errorSection.classList.add("hidden");

    try {
      const res = await fetch("/api/reflect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          mood_id: mood.id, 
          context: "" 
        })
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const message = errorData.detail 
          ? (typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail))
          : `Server error (${res.status})`;
        throw new Error(message);
      }

      const data = await res.json();
      displayResponse(mood, data);
    } catch (err) {
      showError(err.message || "Failed to establish bridge to the archive.");
    } finally {
      loadingSection.classList.add("hidden");
    }
  }

  // Display Response Card Content & Dynamic Visuals
  function displayResponse(mood, data) {
    if (responseKicker) {
      responseKicker.textContent = `ON ${mood.label.toUpperCase()}`;
      responseKicker.style.color = mood.color;
    }
    
    let htmlContent = "";
    
    // Format text paragraphs
    const textResponse = data.response || data.text || "";
    if (textResponse) {
      const paragraphs = textResponse
        .split("\n\n")
        .map((p) => `<p>${p.trim()}</p>`)
        .join("");
      htmlContent += paragraphs;
    }

    // Embed Pollinations visual if returned
    const imageUrl = data.image_url || data.image_prompt_url;
    if (imageUrl) {
      htmlContent += `
        <div class="response-card__image-wrap">
          <img 
            src="${imageUrl}" 
            alt="Minimalist illustration representing calm and resolution for ${mood.label}" 
            loading="lazy" 
          />
        </div>
      `;
    }

    if (responseBody) {
      responseBody.innerHTML = htmlContent;
    }

    if (responseMeta) {
      responseMeta.textContent = "Synthesized via Cognee Graph Memory & Google Gemini API";
    }

    responseSection.classList.remove("hidden");

    // Accessibility focus transition
    const card = responseSection.querySelector(".response-card");
    if (card) {
      card.focus();
    }
  }

  // Render Error Message State
  function showError(message) {
    if (errorText) {
      errorText.textContent = message;
    }
    errorSection.classList.remove("hidden");
  }

  // Recalibrate / Reset View
  if (againBtn) {
    againBtn.addEventListener("click", () => {
      responseSection.classList.add("hidden");
      errorSection.classList.add("hidden");
      if (mandalaContainer.parentElement) {
        mandalaContainer.parentElement.classList.remove("hidden");
      }
    });
  }

  // Initialize
  renderMandala();
});