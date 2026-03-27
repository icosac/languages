const menuToggle = document.getElementById("menu-toggle");
const mobileNav = document.getElementById("mobile-nav");
const profileMenuButton = document.getElementById("profile-menu-button");
const profileMenu = document.getElementById("profile-menu");

if (menuToggle && mobileNav) {
  menuToggle.addEventListener("click", () => {
    mobileNav.classList.toggle("hidden");
  });
}

if (profileMenuButton && profileMenu) {
  const closeProfileMenu = () => {
    profileMenu.classList.add("hidden");
    profileMenuButton.setAttribute("aria-expanded", "false");
  };

  profileMenuButton.addEventListener("click", (event) => {
    event.stopPropagation();
    const isHidden = profileMenu.classList.contains("hidden");
    if (isHidden) {
      profileMenu.classList.remove("hidden");
      profileMenuButton.setAttribute("aria-expanded", "true");
    } else {
      closeProfileMenu();
    }
  });

  document.addEventListener("click", (event) => {
    if (
      !profileMenu.classList.contains("hidden") &&
      !profileMenu.contains(event.target) &&
      !profileMenuButton.contains(event.target)
    ) {
      closeProfileMenu();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeProfileMenu();
    }
  });
}
