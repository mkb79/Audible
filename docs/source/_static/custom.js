/**
 * Custom JavaScript for Audible Documentation
 * Enhances the copy button behavior and adds theme switcher
 */

document.addEventListener("DOMContentLoaded", function () {
  // ==========================================================================
  // Theme Switcher
  // ==========================================================================

  // Get saved theme or default to 'system'
  function getTheme() {
    return localStorage.getItem("audible-docs-theme") || "system";
  }

  // Save theme preference
  function saveTheme(theme) {
    localStorage.setItem("audible-docs-theme", theme);
  }

  // Apply theme to document
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);

    // Update active button state
    const buttons = document.querySelectorAll(".theme-switch-btn");
    buttons.forEach((btn) => {
      btn.classList.remove("active");
      if (btn.dataset.theme === theme) {
        btn.classList.add("active");
      }
    });
  }

  // Get system preference
  function getSystemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  // Apply theme based on preference
  function updateTheme() {
    const savedTheme = getTheme();
    const actualTheme = savedTheme === "system" ? getSystemTheme() : savedTheme;
    applyTheme(actualTheme);
  }

  // Create theme switcher HTML
  function createThemeSwitcher() {
    const themeSwitcher = document.createElement("div");
    themeSwitcher.className = "theme-switcher";
    themeSwitcher.innerHTML = `
            <div class="theme-switch-container">
                <button class="theme-switch-btn" data-theme="light" title="Light Mode" aria-label="Switch to light mode">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="5"></circle>
                        <line x1="12" y1="1" x2="12" y2="3"></line>
                        <line x1="12" y1="21" x2="12" y2="23"></line>
                        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                        <line x1="1" y1="12" x2="3" y2="12"></line>
                        <line x1="21" y1="12" x2="23" y2="12"></line>
                        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                    </svg>
                    <span>Hell</span>
                </button>
                <button class="theme-switch-btn" data-theme="dark" title="Dark Mode" aria-label="Switch to dark mode">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                    </svg>
                    <span>Dunkel</span>
                </button>
                <button class="theme-switch-btn" data-theme="system" title="System Theme" aria-label="Use system theme">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                        <line x1="8" y1="21" x2="16" y2="21"></line>
                        <line x1="12" y1="17" x2="12" y2="21"></line>
                    </svg>
                    <span>System</span>
                </button>
            </div>
        `;

    // Insert after the search box or at top of sidebar
    const sidebar = document.querySelector(".wy-side-nav-search");
    if (sidebar) {
      sidebar.appendChild(themeSwitcher);
    }

    // Add click handlers
    const buttons = themeSwitcher.querySelectorAll(".theme-switch-btn");
    buttons.forEach((button) => {
      button.addEventListener("click", function () {
        const theme = this.dataset.theme;
        saveTheme(theme);
        updateTheme();
      });
    });
  }

  // Initialize theme
  createThemeSwitcher();
  updateTheme();

  // Listen for system theme changes
  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", function () {
      if (getTheme() === "system") {
        updateTheme();
      }
    });

  // ==========================================================================
  // Copy Button Enhancement
  // ==========================================================================

  const copyButtons = document.querySelectorAll("button.copybtn");

  copyButtons.forEach(function (button) {
    // Store original text
    const originalHTML = button.innerHTML;

    // Add "Copy" text if not present
    if (!button.textContent || button.textContent.trim() === "") {
      button.textContent = "Copy";
    }

    // Handle click events for better feedback
    button.addEventListener("click", function () {
      // Change button appearance on click
      button.classList.add("success");
      button.textContent = "✓ Copied!";

      // Reset after 2 seconds
      setTimeout(function () {
        button.classList.remove("success");
        button.innerHTML = originalHTML || "📋 Copy";
      }, 2000);
    });

    // Add hover title for accessibility
    button.setAttribute("title", "Copy code to clipboard");
    button.setAttribute("aria-label", "Copy code to clipboard");
  });
});
