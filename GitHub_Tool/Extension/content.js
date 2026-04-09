function extractCommits() {
    const commits = [];

    document.querySelectorAll('.TimelineItem').forEach(item => {
        const message = item.querySelector('.Link--primary')?.innerText;
        const author = item.querySelector('.commit-author')?.innerText;
        const time = item.querySelector('relative-time')?.innerText;

        if (message) {
            commits.push({ message, author, time });
        }
    });

    return commits;
}

// Send data to UI
window.addEventListener("load", () => {
    const commits = extractCommits();

    const event = new CustomEvent("COMMITS_READY", {
        detail: commits
    });

    window.dispatchEvent(event);
});