document.querySelectorAll('[data-account-form]').forEach(function (form) {
    form.addEventListener('submit', function () {
        var button = form.querySelector('button[type="submit"]');
        var status = form.querySelector('[data-submit-status]');
        button.disabled = true;
        if (status) { status.textContent = button.dataset.submitLabel || 'Salvando…'; }
    });
});
window.addEventListener('pageshow', function () {
    document.querySelectorAll('[data-account-form] button[type="submit"]').forEach(function (button) { button.disabled = false; });
});
var errors = document.querySelector('.errorlist');
if (errors) {
    errors.setAttribute('role', 'alert');
    errors.setAttribute('tabindex', '-1');
    errors.focus();
}
