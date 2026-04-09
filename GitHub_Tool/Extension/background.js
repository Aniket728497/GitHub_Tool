chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "SUMMARIZE") {
        // future: call OpenAI / local model
        sendResponse({ summary: "AI summary here" });
    }
});