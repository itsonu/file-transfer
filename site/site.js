// Point the main download button at the visitor's OS, and make code blocks copyable.
(() => {
  const ua = navigator.userAgent;
  const platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "";
  const os = /win/i.test(platform) || /Windows/.test(ua)
    ? "windows"
    : /mac/i.test(platform) || /Mac OS X/.test(ua)
      ? "mac"
      : /linux/i.test(platform) && !/Android/.test(ua)
        ? "linux"
        : null;
  const names = { windows: "Windows", mac: "macOS", linux: "Linux" };
  const card = os && document.querySelector(`.dl[data-os="${os}"]`);
  const isPhone = /Android|iPhone|iPad/.test(ua);

  if (card && !isPhone) {
    card.classList.add("is-yours");
    const button = document.getElementById("primary-download");
    button.href = card.href;
    document.getElementById("primary-download-label").textContent = `Download for ${names[os]}`;
    document.getElementById("primary-download-note").textContent =
      "Free · ~13 MB · no Python needed · other platforms below";
  } else if (isPhone) {
    // Phones are the *other* device: they only need a browser.
    document.getElementById("primary-download-label").textContent = "Get it for your computer";
    document.getElementById("primary-download").href = "#download";
    document.getElementById("primary-download-note").textContent =
      "Your phone doesn’t need anything — just scan the QR code the computer shows.";
  }

  for (const button of document.querySelectorAll(".copy")) {
    button.addEventListener("click", async () => {
      const text = document.getElementById(button.dataset.copy).textContent;
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Select & copy";
      }
      setTimeout(() => {
        button.textContent = "Copy";
      }, 1600);
    });
  }
})();
