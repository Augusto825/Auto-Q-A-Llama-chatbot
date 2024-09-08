const express = require('express');
const { LMStudioClient } = require("@lmstudio/sdk");

const app = express();
app.use(express.json());
const port = 3000;

async function main() {
  try {
    const client = new LMStudioClient();
    const model = await client.llm.load("monal04/llama-2-7b-chat.Q4_0.gguf-GGML/llama-2-7b-chat.Q4_0.gguf");

    app.post('/predict', async (req, res) => {
      try {
        const question = req.body.question;
        if (!question) {
          res.status(400).send({ error: 'No question provided' });
          return;
        }

        const prediction = model.respond([
          { role: "system", content: "You are a helpful AI assistant." },
          { role: "user", content: question },
        ]);

        let responseText = '';
        for await (const text of prediction) {
          responseText += text;
        }

        res.send(responseText);
      } catch (error) {
        console.error('Error generating answer:', error);
        res.status(500).send({ error: 'Internal Server Error' });
      }
    });

    app.listen(port, () => {
      console.log(`Server listening on port ${port}`);
    });
  } catch (error) {
    console.error('Error starting server:', error);
    console.log('Error occurred. Please check the logs for more information.');
    console.log('Press any key to continue...');
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', () => {
      process.exit(0);
    });
  }
}

main();