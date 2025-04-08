/**
 * Placeholder function for getting AI comments on document content.
 * In a real application, this would involve sending the content to an AI service.
 * @param {string | object} documentContent The content of the document (format TBD).
 * @returns {Promise<Array<object>>} A promise that resolves to an array of comment objects.
 */
async function getAiComments(documentContent) {
    console.log("AI Service: Received content for analysis (placeholder).");
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));

    // Return hardcoded comments for now
    return [
        { text: "This opening paragraph is strong and engaging.", context: "Paragraph 1" },
        { text: "Consider rephrasing this sentence for clarity.", context: "Paragraph 3, Sentence 2" },
        { text: "Excellent point made here.", context: "Paragraph 5" },
        { text: "Suggestion: Add a concluding remark to summarize.", context: "End of document" }
    ];
}

module.exports = {
    getAiComments,
}; 