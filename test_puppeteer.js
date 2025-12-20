const puppeteer = require('puppeteer');

(async () => {
  const url = "https://passerelle.centris.ca/redirect.aspx?NoMLS=23215645&Lang=F&source=centris.ca";
  
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle2' });
  
  const finalUrl = page.url();
  console.log("Final URL:", finalUrl);
  
  await browser.close();
})();
