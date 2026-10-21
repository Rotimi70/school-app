(function () {
  var sidebar = document.getElementById("sidebar");
  var scrim = document.getElementById("scrim");
  var toggle = document.getElementById("menu-toggle");

  function setNav(open) {
    if (!sidebar) return;
    sidebar.classList.toggle("open", open);
    if (scrim) scrim.classList.toggle("show", open);
  }
  if (toggle) toggle.addEventListener("click", function () { setNav(!sidebar.classList.contains("open")); });
  if (scrim) scrim.addEventListener("click", function () { setNav(false); });

  // Confirm before destructive actions: <form data-confirm="Are you sure?">
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  // Attendance: mark everyone with one click
  document.querySelectorAll("[data-mark-all]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var value = btn.getAttribute("data-mark-all");
      document.querySelectorAll('input[type=radio][value="' + value + '"]').forEach(function (r) { r.checked = true; });
    });
  });

  // Fade flash messages after a few seconds
  document.querySelectorAll(".flash.success").forEach(function (el) {
    setTimeout(function () { el.style.transition = "opacity .4s"; el.style.opacity = "0"; }, 4500);
    setTimeout(function () { el.remove(); }, 5000);
  });
})();
