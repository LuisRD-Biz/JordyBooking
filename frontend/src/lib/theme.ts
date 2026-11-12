const KEY = 'jordy.theme';
export type Theme = 'light' | 'dark';

export const storedTheme = (): Theme => (localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light');

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(KEY, theme);
  const background = getComputedStyle(document.documentElement).getPropertyValue('background-color');
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', background || '');
}
