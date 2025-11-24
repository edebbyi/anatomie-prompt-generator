// ▶️ CONFIG - Keep the same interface
const { numOfPrompts, renderer } = input.config();

// 🔑 Tables - Only need Prompts and History for writing
const promptsTbl = base.getTable("Prompts");
const historyTbl = base.getTable("History");

// 🌐 Service URL - Replace with your Render URL after deployment
const SERVICE_URL = "https://your-app-name.onrender.com";

// 📡 Call FastAPI Service
console.log(`🚀 Requesting ${numOfPrompts} prompts for renderer "${renderer}"...`);

let response = await fetch(`${SERVICE_URL}/generate-prompts`, {
  method: "POST",
  headers: { 
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    request_id: null,
    num_prompts: numOfPrompts,
    renderer: renderer
  })
});

// ⚠️ Error Handling
if (!response.ok) {
  let errorText = await response.text();
  throw new Error(`Service returned ${response.status}: ${errorText}`);
}

let data = await response.json();

// ✅ Validate Response
if (!data.prompts || !Array.isArray(data.prompts)) {
  throw new Error("Invalid response format: missing 'prompts' array");
}

if (data.prompts.length !== numOfPrompts) {
  throw new Error(`Expected ${numOfPrompts} prompts, got ${data.prompts.length}`);
}

// 💾 Write Prompts to Airtable
console.log(`📝 Writing ${data.prompts.length} prompts to Airtable...`);

for (let p of data.prompts) {
  // Validate prompt object
  if (!p.promptText || !p.designerId || !p.garmentId || !p.promptStructureId || !p.renderer) {
    console.error("❌ Invalid prompt object:", p);
    continue;
  }

  // Create Prompt record
  let newId = await promptsTbl.createRecordAsync({
    "New Prompt": p.promptText,
    "Designer": [{ id: p.designerId }],
    "Garment": [{ id: p.garmentId }],
    "Renderer": { name: p.renderer },
    "Prompt Structure": [{ id: p.promptStructureId }]
  });

  // Backfill Prompt ID with record ID
  await promptsTbl.updateRecordAsync(newId, { 
    "Prompt ID": newId 
  });

  // Create History record
  await historyTbl.createRecordAsync({
    "Prompt ID": newId,
    "Designer": [{ id: p.designerId }],
    "Garment": [{ id: p.garmentId }],
    "Renderer": { name: p.renderer },
    "Prompt Structure": [{ id: p.promptStructureId }],
    "Date": new Date()
  });
}

console.log(`✅ Successfully generated ${data.prompts.length} prompt(s) for renderer "${renderer}".`);

