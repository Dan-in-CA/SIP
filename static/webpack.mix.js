const mix = require('laravel-mix');

/*
 |--------------------------------------------------------------------------
 | Mix Asset Management
 |--------------------------------------------------------------------------
 |
 | Mix provides a clean, fluent API for defining some Webpack build steps
 | for your Laravel application. By default, we are compiling the Sass
 | file for the application as well as bundling up all the JS files.
 |
 */

mix.js('assets/app.js', 'dist/js')
    .sass('assets/base.scss', 'dist/css')
    .copyDirectory('assets/icons/','dist/icons')

mix.copy('node_modules/@fortawesome/fontawesome-free/webfonts', 'dist/fonts/fontAwesome')



mix.options({
    processCssUrls: false
});
