import { test, expect } from '@playwright/test';
const pages=[['/','Energy in balance.'],['/renewables','Renewable energy analytics'],['/load','Stay ahead of every peak.'],['/battery','Battery energy storage'],['/grid','Smart grid control center'],['/monitoring','See beyond the energy balance.'],['/maintenance','Faults & predictive maintenance'],['/optimization','Better energy. By calculation.'],['/simulation','Your grid. Your what-if.'],['/reports','Reports & data workspace']];
test('all control-center pages render integrated backend data without browser errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const [path,title] of pages){await page.goto(path);await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible();await expect(page.getByText('Simulation mode',{exact:true})).toBeVisible();await page.waitForTimeout(350);expect(await page.locator('body').evaluate(e=>e.scrollWidth<=innerWidth+1)).toBeTruthy();}
 expect(errors).toEqual([]);
});
test('overview interactive charts, topology, theme and clock work',async({page})=>{
 await page.goto('/');await expect(page.getByRole('heading',{name:'Energy in balance.'})).toBeVisible();
 await page.getByRole('button',{name:'History',exact:true}).click();await expect(page.getByText('RECENT SIMULATED HISTORY')).toBeVisible();
 await page.getByRole('button',{name:'Inspect Solar array'}).click();await expect(page.locator('.topology-detail')).toContainText('Solar array');
 await page.getByRole('button',{name:'Toggle light and dark theme'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.getByRole('button',{name:'Toggle light and dark theme'}).click();
 await page.getByRole('button',{name:'+1 hour',exact:true}).click();await expect(page.getByRole('status')).toContainText('One simulated hour completed');
 await page.screenshot({path:'../docs/screenshots/overview-desktop.png',fullPage:true});
});
test('all seven scenarios update actual backend results and preserve constraints',async({page,request})=>{
 const baseline=await (await request.get('/api/dashboard')).json();
 for(const scenario of ['low_solar','high_demand','surplus','low_battery','outage','abnormal','normal']){
  const response=await request.post('/api/simulation',{data:{scenario,horizon:12}});expect(response.ok()).toBeTruthy();const d=await response.json();expect(d.config.scenario).toBe(scenario);expect(d.optimization.summary.max_balance_residual_kw).toBeLessThan(0.00001);
  if(scenario==='high_demand'){expect(d.config.demand_factor).toBe(1.65);expect(d.optimization.summary.demand_kwh).toBeGreaterThan(baseline.optimization.summary.demand_kwh*1.5);}
  await page.goto('/optimization');await expect(page.getByRole('heading',{name:'Better energy. By calculation.'})).toBeVisible();
  if(scenario==='outage')await expect(page.locator('.stats-grid')).toContainText('Grid dependency');
 }
});
test('simulation form applies weather and battery controls',async({page})=>{
 await page.goto('/simulation');await expect(page.getByRole('heading',{name:'Your grid. Your what-if.'})).toBeVisible();
 await page.getByRole('button',{name:/Low solar Heavy/}).click();await expect(page.getByLabel('Cloud cover',{exact:true})).toHaveValue('85');
 await page.getByRole('spinbutton',{name:'Capacity (kWh)',exact:true}).fill('1500');await page.getByRole('button',{name:'Apply & optimize'}).click();await expect(page.getByRole('status')).toContainText('Scenario applied');
 await page.goto('/battery');await expect(page.locator('.config-grid')).toContainText('1,500');
});
test('maintenance plan can be created and completed',async({page})=>{
 await page.goto('/maintenance');await page.getByRole('button',{name:'Plan inspection',exact:true}).click();await page.getByLabel('Inspection action').fill('Browser validation: inspect simulated transformer cooling.');await page.getByRole('button',{name:'Save inspection plan'}).click();await expect(page.getByRole('status')).toContainText('Maintenance inspection added');const row=page.getByRole('row').filter({hasText:'Browser validation: inspect simulated transformer cooling.'}).filter({has:page.getByRole('button',{name:'Mark complete'})}).first();await row.getByRole('button',{name:'Mark complete'}).click();await expect(page.getByRole('row').filter({hasText:'Browser validation: inspect simulated transformer cooling.'}).first()).toContainText('completed');
});
test('CSV upload validates and generates downloadable predictions',async({page})=>{
 await page.goto('/reports');await expect(page.getByRole('heading',{name:'Reports & data workspace'})).toBeVisible();const response=await page.request.get('/api/upload/template?target=solar');const csv=await response.text();await page.getByLabel('Upload compatible CSV').setInputFiles({name:'solar.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});await page.getByRole('button',{name:'Validate & predict'}).click();await expect(page.getByRole('heading',{name:'CSV prediction results'})).toBeVisible();await expect(page.getByText(/Validation passed/)).toBeVisible();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download weekly CSV'}).click();expect((await download).suggestedFilename()).toBe('heliogrid-weekly.csv');
});
test('mobile navigation and pages remain usable',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.getByRole('heading',{name:'Energy in balance.'})).toBeVisible();await page.screenshot({path:'../docs/screenshots/overview-mobile.png',fullPage:true});await page.getByRole('button',{name:'Open navigation'}).click();await page.getByRole('link',{name:'Simulation lab',exact:true}).click();await expect(page.getByRole('heading',{name:'Your grid. Your what-if.'})).toBeVisible();expect(await page.locator('body').evaluate(e=>e.scrollWidth<=innerWidth+1)).toBeTruthy();
});
