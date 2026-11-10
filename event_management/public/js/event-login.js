// EventPro custom login redirect
(function () {
    const currentUrl = new URL(window.location.href);

    // Redirect to the custom login page after authentication.
    if (!currentUrl.searchParams.has("redirect-to")) {
        currentUrl.searchParams.set("redirect-to", "/event-login");

        window.history.replaceState(
            {},
            document.title,
            currentUrl.toString()
        );
    }
})();