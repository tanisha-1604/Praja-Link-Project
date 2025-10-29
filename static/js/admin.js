document.addEventListener('DOMContentLoaded', function() {
    const hamburgerMenu = document.getElementById('hamburgerMenu');
    const mainNav = document.getElementById('mainNav');

        hamburgerMenu.addEventListener('click', function() {
            // Toggles the 'active' class on the navigation menu
            mainNav.classList.toggle('active');
        });
    });

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-link]").forEach((btn) => {
    btn.addEventListener("click", () => {
      window.location.href = btn.dataset.link;
    });
  });
});
