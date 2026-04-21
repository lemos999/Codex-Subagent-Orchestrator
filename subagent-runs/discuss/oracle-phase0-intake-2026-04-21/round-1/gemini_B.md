YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.
Attempt 1 failed: You have exhausted your capacity on this model.. Retrying after 11447ms...
Attempt 2 failed: You have exhausted your capacity on this model.. Retrying after 22106ms...
Attempt 3 failed: You have exhausted your capacity on this model.. Retrying after 32254ms...
Attempt 4 failed: You have exhausted your capacity on this model.. Retrying after 34713ms...
Attempt 5 failed: You have exhausted your capacity on this model.. Retrying after 30416ms...
Attempt 6 failed: You have exhausted your capacity on this model.. Retrying after 34100ms...
Attempt 7 failed: You have exhausted your capacity on this model.. Retrying after 33784ms...
Attempt 8 failed: You have exhausted your capacity on this model.. Retrying after 31710ms...
Attempt 9 failed: You have exhausted your capacity on this model.. Retrying after 33883ms...
Attempt 10 failed: You have exhausted your capacity on this model.. Max attempts reached
Error when talking to Gemini API Full report available at: C:\Users\haj\AppData\Local\Temp\gemini-client-error-Turn.run-sendMessageStream-2026-04-21T03-08-05-936Z.json RetryableQuotaError: You have exhausted your capacity on this model.
    at classifyGoogleError (file:///C:/Users/haj/AppData/Roaming/npm/node_modules/@google/gemini-cli/bundle/chunk-2P3YD5SP.js:273978:18)
    at retryWithBackoff (file:///C:/Users/haj/AppData/Roaming/npm/node_modules/@google/gemini-cli/bundle/chunk-2P3YD5SP.js:274577:31)
    at process.processTicksAndRejections (node:internal/process/task_queues:103:5)
    at async GeminiChat.makeApiCallAndProcessStream (file:///C:/Users/haj/AppData/Roaming/npm/node_modules/@google/gemini-cli/bundle/chunk-2P3YD5SP.js:309884:28)
    at async GeminiChat.streamWithRetries (file:///C:/Users/haj/AppData/Roaming/npm/node_modules/@google/gemini-cli/bundle/chunk-2P3YD5SP.js:309727:29)
    at async Turn.run (file:///C:/Users/haj/AppData/Roaming/npm/node_modules/@google/gemini-cli/bundle/chunk-2P3YD5SP.js:310214:24)
    at async GeminiClient.processTurn (file:///C:/Users/haj/AppData/Roaming/npm/node_modules/@google/gemini-cli/bundle/chunk-2P3YD5SP.js:314287:22)
    at async GeminiClient.sendMessageStream (file:///C:/Users/haj/AppData/Roaming/npm/node_modules/@google/gemini-cli/bundle/chunk-2P3YD5SP.js:314400:14)
    at async file:///C:/Users/haj/AppData/Roaming/npm/node_modules/@google/gemini-cli/bundle/gemini.js:9701:26
    at async main (file:///C:/Users/haj/AppData/Roaming/npm/node_modules/@google/gemini-cli/bundle/gemini.js:14721:5) {
  cause: {
    code: 429,
    message: 'You have exhausted your capacity on this model.',
    details: [ [Object], [Object] ]
  },
  retryDelayMs: 10000
}
An unexpected critical error occurred:[object Object]
