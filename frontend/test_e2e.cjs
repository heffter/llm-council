const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Opening LLM Council frontend...');
  await page.goto('http://localhost:5173');
  await page.waitForLoadState('networkidle');

  // Click New Conversation button
  console.log('Clicking New Conversation...');
  await page.click('text=New Conversation');
  await page.waitForTimeout(2000);

  await page.screenshot({ path: '/tmp/llm_council_new_conv.png', fullPage: true });
  console.log('Screenshot saved to /tmp/llm_council_new_conv.png');

  // Look for input field now
  const inputField = await page.locator('textarea').first();
  const hasInput = await inputField.count() > 0;
  console.log('Has input field (textarea):', hasInput);

  if (hasInput) {
    console.log('\nTyping test message...');
    await inputField.fill('What is 2+2? Give a brief answer.');
    await page.screenshot({ path: '/tmp/llm_council_typing.png', fullPage: true });

    // Find and click send button
    const sendButton = await page.locator('button[type="submit"]').first();
    if (await sendButton.count() > 0) {
      console.log('Clicking send button...');
      await sendButton.click();

      console.log('Waiting for LLM responses (90 seconds)...');

      // Take screenshots periodically
      for (let i = 0; i < 9; i++) {
        await page.waitForTimeout(10000);
        const screenshotPath = '/tmp/llm_council_progress_' + (i+1) + '.png';
        await page.screenshot({ path: screenshotPath, fullPage: true });

        const text = await page.textContent('body');
        console.log('Progress ' + ((i+1)*10) + 's:');
        if (text.includes('Stage 1')) console.log('  - Stage 1 visible');
        if (text.includes('Stage 2')) console.log('  - Stage 2 visible');
        if (text.includes('Stage 3')) console.log('  - Stage 3 visible');
        if (text.includes('Error')) console.log('  - Error visible');
        if (text.includes('openai') || text.includes('gpt')) console.log('  - OpenAI response');
        if (text.includes('anthropic') || text.includes('claude')) console.log('  - Anthropic response');
        if (text.includes('gemini')) console.log('  - Gemini response');
      }

      await page.screenshot({ path: '/tmp/llm_council_final.png', fullPage: true });
      console.log('\nFinal screenshot saved');
    }
  }

  await browser.close();
  console.log('\nTest complete!');
})();
