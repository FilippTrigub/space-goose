const OpenAI = require("openai");

const systemPrompt = `
You are an expert in drill down questions and your job is to review the markdown text below following these guildelines:

1. Point out statements which have assumptions, vagueness, ambiguous, have slippery terms, difficult concepts
2. Review the document and ensure it contains a reason why it is worth our time to focus on now, outlines who should participate, and what the desired outcome should be
3. Review the document and ensure it has a clear problem statement and solution which addresses the problem statment
4. Point out where the document does not have any references to evidence to back up its statements
5. Review the document and ensure it details the consequences of the current problem and the impact on stakeholders and customers in the short/mid and long term
6. Document should contain a risk assessment and its potential harm/impact
7. Review the document and ensure it has 1 or more clearly outlined actions to address the problem statement
8. Document should clearly define accountability, who should sign off and who should execute the solution
9. Document must atleast have a structure of executive summary, problem statement and solution proposal

Review the following text and return all findings as a collection of json objects named 'findings', containing issue type labelled 'issue_type', description labelled 'desc', the text containing the issue labelled 'text', proposed change labelled 'change' if possible include a replacement text suggestion labelled 'suggestion'; Respond ONLY with the JSON object containing the 'findings' array.
`;

// Initialize the OpenAI client to point to the local endpoint
const client = new OpenAI({
  baseURL: "http://localhost:12434/engines/v1",
  apiKey: "irrelevant", // API key is required, even if the local model doesn't use it
});

/*
 * Extracts plain text content from the complex document JSON structure.
 * @param {Array<object>} documentJson The array representing document structure.
 * @returns {string} The extracted plain text content.
 */
function extractTextFromDocumentJson(documentJson) {
  if (!Array.isArray(documentJson)) {
    console.warn("AI Service: Input document content is not an array. Attempting to treat as string.");
    // If it's not an array, maybe it's already a string or simple object?
    // Handle non-array input gracefully, return as is or stringified.
    return typeof documentJson === 'string' ? documentJson : JSON.stringify(documentJson);
  }

  let extractedText = "";
  for (const element of documentJson) {
    if (element.paragraph && element.paragraph.elements) {
      for (const pElement of element.paragraph.elements) {
        if (pElement.textRun && pElement.textRun.content) {
          extractedText += pElement.textRun.content;
        }
      }
      // Add a newline after each paragraph block for readability, if not already ending with one.
      if (!extractedText.endsWith('\n')) {
          extractedText += '\n';
      }
    }
    // Add logic here to handle other element types if necessary (e.g., tables, lists)
  }
  return extractedText.trim(); // Trim leading/trailing whitespace
}

/**
 * Uses an AI model via an OpenAI-compatible endpoint to analyze document content.
 * @param {string | Array<object>} documentContent The markdown content or JSON structure of the document.
 * @returns {Promise<Array<object>>} A promise that resolves to an array of finding objects.
 */
async function getAiComments(documentContent) {
    console.log("AI Service: Received content for analysis.");

    // Extract plain text if the input is the complex JSON structure
    const plainTextContent = extractTextFromDocumentJson(documentContent);

    console.log("AI Service: Sending extracted text for analysis...");
    // console.log("--- Extracted Text ---"); // Optional: log extracted text for debugging
    // console.log(plainTextContent);
    // console.log("----------------------");

    const messages = [
        { role: "system", content: systemPrompt },
        { role: "user", content: plainTextContent }, // Use the extracted plain text
    ];

    try {
        const completion = await client.chat.completions.create({
            model: "ai/mistral:latest", // Specify the model to use
            messages: messages,
            temperature: 0.5, // Keep the temperature setting
            response_format: { type: "json_object" }, // Request JSON output
        });

        const responseContent = completion.choices[0]?.message?.content;

        if (!responseContent) {
            console.error("AI Service: No content received from AI model.");
            return [];
        }

        try {
            const result = JSON.parse(responseContent);
            // Assuming the LLM returns { findings: [...] }
            if (result && typeof result === 'object' && Array.isArray(result.findings)) {
                console.log(`AI Service: Received ${result.findings.length} findings.`);
                return result.findings;
            } else {
                console.error("AI Service: Unexpected JSON structure from LLM:", result);
                return []; // Return empty if structure is wrong
            }
        } catch (parseError) {
            console.error("AI Service: Failed to parse JSON response from AI model:", parseError);
            console.error("AI Service: Raw response content:", responseContent);
            return []; // Return empty array on parse error
        }

    } catch (error) {
        console.error("AI Service: Error calling AI model:", error);
        // Log more details if available, e.g., error response from the server
        if (error.response) {
            console.error("AI Service: Error response data:", error.response.data);
            console.error("AI Service: Error response status:", error.response.status);
        }
        throw error; // Re-throw the error for the caller to handle
    }
}

module.exports = {
    getAiComments,
}; 