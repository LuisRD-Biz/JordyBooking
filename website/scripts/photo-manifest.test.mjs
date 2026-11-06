import assert from 'node:assert/strict';
import test from 'node:test';
import {publicPhotos, selectPhotos, validateManifest} from '../.build/prerender.js';

const sample = {
  id:'fixture', base:'/media/test', category:'Bodas', alt:'Pareja en el jardín', title:'Jardín',
  width:1200, height:800, widths:[600,1200], orientation:'landscape', position:1,
  isHero:false, featured:false, visible:true, focal:'center'
};
const photo = (id, overrides = {}) => ({...sample, id, isHero:false, featured:false, ...overrides});

test('hero, chapter and archive use independent roles and editorial order', () => {
  const first = photo('a', {position:1});
  const last = photo('z', {position:12});
  const lead = photo('lead', {featured:true, position:2});
  const hero = photo('cover', {isHero:true, featured:false, position:99});
  const selected = selectPhotos([last, lead, hero, first]);
  assert.equal(selected.hero, hero);
  assert.deepEqual(selected.chapterPhotos, [lead]);
  assert.deepEqual(selected.portfolio, [first, last]);
});

test('hiding the cover never promotes a detail by accident', () => {
  const visible = photo('detail');
  const selected = selectPhotos([visible, photo('cover', {visible:false, isHero:true})]);
  assert.equal(selected.hero, undefined);
  assert.deepEqual(selected.photographs, [visible]);
  assert.deepEqual(selectPhotos([]).chapterPhotos, []);
});

test('duplicate ids including hidden records and competing visible covers fail validation', () => {
  assert.throws(() => validateManifest([sample, {...sample, visible:false}]));
  assert.throws(() => validateManifest([photo('a', {isHero:true}), photo('b', {isHero:true})]));
});

test('dimensions, variants, alt and public paths must match the manifest contract', () => {
  for (const changes of [
    {width:NaN}, {height:0}, {orientation:'square'}, {position:-1}, {alt:' '},
    {widths:[]}, {widths:[560,560]}, {widths:[800,400]}, {widths:[sample.width+1]},
    {base:'/media/../private'}, {base:'https://invalid.example/image'}
  ]) assert.throws(() => validateManifest([{...sample, ...changes}]));
  assert.doesNotThrow(() => validateManifest(publicPhotos()));
});
