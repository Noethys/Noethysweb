document.addEventListener("DOMContentLoaded", function(event) {
    window.setTimeout(function () {
        const label = document.querySelector(`label[for="id_user_permissions"]`);
        label.parentNode.prepend(label);
    }, 100);
});
