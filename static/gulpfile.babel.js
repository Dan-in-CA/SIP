const gulp = require('gulp');
const sass = require('gulp-sass');
const browserSync = require('browser-sync').create();
const uglify = require('gulp-uglify-es').default;
const del = require('del');
const autoprefixer = require('gulp-autoprefixer');
const cssnano = require('gulp-cssnano');
const minify = require('gulp-minify');
const concat = require('gulp-concat');
const gulpIf = require('gulp-if');
const babel = require('gulp-babel');
const isProd = process.env.NODE_ENV === 'prod';
const sourcemaps = require('gulp-sourcemaps');

// ------------ Development Tasks -------------
// Compile Sass into CSS
const css = function () {
    console.log('Building css');
    return gulp.src(['./assets/app.scss'])
        .pipe(gulpIf(!isProd, sourcemaps.init()))
        .pipe(sass({
            includePaths: ['node_modules'],
            // outputStyle: 'expanded',
            sourceComments: 'map',
            sourceMap: 'sass',
            outputStyle: 'nested'
        }).on('error', sass.logError))
        .pipe(gulpIf(isProd, autoprefixer('last 2 versions')))
        .pipe(gulpIf(!isProd, sourcemaps.write()))
        .pipe(gulpIf(isProd, cssnano()))
        .pipe(gulp.dest("dist/css/"))
    // .pipe(browserSync.stream());
};


// Places font files in the dist folder
fonts = function () {
    return gulp.src('./assets/fonts/**/*.+(eot|woff|ttf|otf)')
        .pipe(gulp.dest("dist/fonts"))
    // .pipe(browserSync.stream());
};

// Concatenating js files
const js = function () {
    console.log('Building js scripts');
    return gulp.src('./assets/app.js')
        .pipe(babel({presets: ['@babel/env']}))
        .pipe(sourcemaps.init())
        //If concatenating more than one JS file
        .pipe(concat('app.js'))
        .pipe(gulpIf(isProd, uglify()))
        .pipe(sourcemaps.write('./'))
        // .pipe(minify())
        .pipe(gulp.dest('dist/js/'))
    // .pipe(browserSync.stream());
}

// Cleaning/deleting files no longer being used in dist folder
const clean = function () {
    console.log('Removing old files from dist');
    return del('dist/**');
}
// function img() {
//     return gulp.src('src/img/*')
//         .pipe(gulpIf(isProd, imagemin()))
//         .pipe(gulp.dest('docs/img/'));
// }
//
function browserSyncReload(done) {
    browserSync.reload();
    done();
}

const serve = function () {
    browserSync.init({
        open: true,
        server: "./dist"
    });
}
// Watches for changes while gulp is running
const watch = function () {
    // Live reload with BrowserSync

    // runSequence('build')
    gulp.watch('assets/**/*.scss', gulp.series(css, browserSyncReload));
    gulp.watch('assets/**/*.js', gulp.series(js, browserSyncReload));
    // gulp.watch('assets/img/**/*.*', gulp.series(img));

    console.log('Watching for changes');

}


exports.css = css;
exports.js = js;
exports.del = del;
exports.serve = gulp.parallel(css, js, watch, serve);
exports.default = gulp.series(clean, gulp.parallel(css, js, fonts));

