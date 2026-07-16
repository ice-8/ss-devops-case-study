document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("csv_file");
  if (!input) return;
  input.addEventListener("change", () => {
    const button = document.querySelector(".upload-form button");
    if (input.files.length && button) {
      button.textContent = `Process ${input.files[0].name}`;
    }
  });
});
