import { test, expect } from '@playwright/test';

test('dashboard loads and shows main components', async ({ page }) => {
  await page.goto('/');
  
  // Verifica se o título da marca está presente
  await expect(page.locator('.brand-text')).toContainText('Omni Core');
  
  // Verifica se a barra lateral está visível
  await expect(page.locator('nav.sidebar')).toBeVisible();
  
  // Verifica se o grid de monitoramento está visível
  await expect(page.locator('.monitor-grid')).toBeVisible();

  // Verifica se o card de "Now Playing" está presente pelo texto
  await expect(page.getByText('NO AR AGORA')).toBeVisible();
});

test('navigation between tabs works', async ({ page }) => {
  await page.goto('/');
  
  // Clica na aba de Biblioteca (que corresponde ao activeTab === 'acervo')
  await page.getByText('Biblioteca').click();
  
  // Verifica se o título da página mudou para 'Database SQLite' (visto no App.jsx para activeTab === 'acervo')
  await expect(page.locator('h1')).toContainText('Database SQLite');
  
  // Verifica se o componente AcervoPage está visível
  await expect(page.locator('.acervo-page')).toBeVisible();
});

test('api stats are being fetched', async ({ page }) => {
  await page.goto('/');
  
  // Se a API estiver offline, o App.jsx define uma mensagem de erro
  const errorMsg = page.getByText('Conexão com o Servidor Omni Core perdida.');
  await expect(errorMsg).not.toBeVisible();
  
  // Verifica se o card de 'ACERVO TOTAL' está visível
  await expect(page.getByText('ACERVO TOTAL')).toBeVisible();
  
  // Verifica se o valor do acervo total (mesmo que seja 0 inicialmente) está visível
  // O container do valor está logo após o texto 'ACERVO TOTAL'
  const acervoTotal = page.locator('.premium-card').filter({ hasText: 'ACERVO TOTAL' });
  await expect(acervoTotal).toBeVisible();
});
