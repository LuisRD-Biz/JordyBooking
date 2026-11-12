const KEY = 'jordy.theme';
export type Theme = 'light' | 'dark';

export const storedTheme = (): Theme => (localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light');

/** Apply the theme to the whole document (the login screen included) and remember it. */
export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(KEY, theme);
  // Keeps the phone's status bar in step with the page background.
  const background = getComputedStyle(document.documentElement).getPropertyValue('background-color');
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', background || '');
}
