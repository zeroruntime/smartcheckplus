// Load plugins
const { src, dest, watch, parallel, series } = require("gulp");
const browsersync = require("browser-sync").create();
const fileinclude = require("gulp-file-include");
const useref = require("gulp-useref");
const gulpIf = require("gulp-if");
const npmDist = require("gulp-npm-dist");
const postcss = require("gulp-postcss");
const TD_CONFIG = "./tailwind.config.js";
const cssnano = require("cssnano");
const replace = require("gulp-replace");
const del = require("del");
const autoprefixer = require("autoprefixer");
const terser = require("gulp-terser");
const minifyCSS = require("gulp-clean-css");
const tailwindcss = require("tailwindcss");
const concat = require("gulp-concat");
const fs = require("fs");
const path = require("path");

//**************************//
// Set Your Django Paths
//**************************//
const paths = {
  base: {
    base: "./",
    node: "./node_modules",
  },
  src: {
    basesrc: "./src",
    basesrcfiles: "./src/**/*",
    css: "./src/assets/css",
    tailwind: "./src/assets/tailwind/**/*.css",
    js: "./src/assets/js/**/*.js",
    html: "./src/**/*.html",
    fonts: "./src/assets/fonts/**/*",
    assets: "./src/assets/**/*",
    shared: "./src/partials/**/*",
    images: "./src/assets/images/**/*",
  },
  temp: {
    basetemp: "./.temp",
  },
  django: {
    templates: "./templates",
    static: "./static",
    css: "./static/css",
    js: "./static/js",
    images: "./static/images",
    fonts: "./static/fonts",
    libs: "./static/libs",
  }
};

//**************************//
// Compile tailwind to CSS
//**************************//

// function tcss() {
//   return (
//     src(paths.src.tailwind)
//       .pipe(postcss([tailwindcss(TD_CONFIG), require("autoprefixer")]))
//       .pipe(concat({ path: "theme.css" }))
//       .pipe(minifyCSS())
//       .pipe(dest(paths.src.css))
//       .pipe(dest(paths.django.css))  // Also output to Django static folder
//       .pipe(browsersync.stream())
//   );
// }

//**************************//
// Process HTML for Django
//**************************//
function djangoTemplates() {
  return src([paths.src.html, "!./src/partials/**/*"])
    .pipe(
      fileinclude({
        prefix: "@@",
        basepath: "@file",
      })
    )
    // Add Django template tags header
    .pipe(replace(/<html.*?>/i, '{% load static %}\n$&'))

    // Process all types of asset references
    // 1. Handle node_modules references
    .pipe(replace(/src="(.{0,10})node_modules\/(.*?)"/g, 'src="{% static \'libs/$2\' %}"'))
    .pipe(replace(/href="(.{0,10})node_modules\/(.*?)"/g, 'href="{% static \'libs/$2\' %}"'))

    // 2. Handle assets folder references (with and without leading slash)
    .pipe(replace(/src="\/assets\/(.*?)"/g, 'src="{% static \'$1\' %}"'))
    .pipe(replace(/href="\/assets\/(.*?)"/g, 'href="{% static \'$1\' %}"'))
    .pipe(replace(/src="assets\/(.*?)"/g, 'src="{% static \'$1\' %}"'))
    .pipe(replace(/href="assets\/(.*?)"/g, 'href="{% static \'$1\' %}"'))

    // 3. Handle content references (images, js, css) with no assets prefix
    .pipe(replace(/src="(images\/.*?)"/g, 'src="{% static \'$1\' %}"'))
    .pipe(replace(/src="(js\/.*?)"/g, 'src="{% static \'$1\' %}"'))
    .pipe(replace(/href="(css\/.*?)"/g, 'href="{% static \'$1\' %}"'))
    .pipe(replace(/href="(fonts\/.*?)"/g, 'href="{% static \'$1\' %}"'))

    // 4. Handle links to other pages
    .pipe(replace(/href="(.*?)\.html"/g, 'href="{% url \'$1\' %}"'))

    // 5. Fix any double static tags if they occurred
    .pipe(replace(/{% static '{% static '(.*?)' %}' %}/g, '{% static \'$1\' %}'))

    .pipe(dest(paths.django.templates))
    .pipe(browsersync.stream());
}

// Function to manually fix any missed static references
function fixMissedStaticRefs() {
  return src(paths.django.templates + '/**/*.html')
    // Additional patterns that might be missed
    .pipe(replace(/src="(\/.*?\.(?:png|jpg|jpeg|gif|svg|webp))"/g, 'src="{% static \'$1\' %}"'))
    .pipe(replace(/href="(\/.*?\.(?:css|ico))"/g, 'href="{% static \'$1\' %}"'))
    // Clean paths by removing leading slash
    .pipe(replace(/{% static '\/(.+?)' %}/g, '{% static \'$1\' %}'))
    .pipe(dest(paths.django.templates));
}

// Copy libs file from nodemodules to Django static
function copyLibs() {
  return src(npmDist(), { base: paths.base.node }).pipe(dest(paths.django.libs));
}

// Copy images to Django static
function images() {
  return src(paths.src.images).pipe(dest(paths.django.images));
}

// Copy fonts to Django static
function fonts() {
  return src(paths.src.fonts).pipe(dest(paths.django.fonts));
}

// Copy JS to Django static
function js() {
  return src(paths.src.js).pipe(dest(paths.django.js));
}

// Copy CSS to Django static
function css() {
  return src("./src/assets/css/**/*.css").pipe(dest(paths.django.css));
}

// Clean Django static folders
function cleanDjangoStatic(callback) {
  del.sync([
    paths.django.css,
    paths.django.js,
    paths.django.images,
    paths.django.fonts,
    paths.django.libs
  ]);
  callback();
}

// Create Django static folders if they don't exist
function createDjangoFolders(callback) {
  const folders = [
    paths.django.templates,
    paths.django.static,
    paths.django.css,
    paths.django.js,
    paths.django.images,
    paths.django.fonts,
    paths.django.libs
  ];

  folders.forEach(folder => {
    if (!fs.existsSync(folder)) {
      fs.mkdirSync(folder, { recursive: true });
    }
  });

  callback();
}

// Check templates for static asset issues
function checkStaticAssets() {
  console.log("Checking templates for potential static asset issues...");

  // Get all HTML files in templates directory
  const templateFiles = getAllFiles(paths.django.templates);
  let issuesFound = false;

  templateFiles.forEach(file => {
    // Skip base templates or partials if needed
    if (file.includes('_base.html') || file.includes('partials/')) {
      return;
    }

    const content = fs.readFileSync(file, 'utf8');

    // Check for potentially missing static tags
    const patterns = [
      { regex: /src="(\/?\w+\/[^{%].*?)"/g, type: 'SRC attribute without static tag' },
      { regex: /href="(\/?\w+\/[^{%#].*?)"/g, type: 'HREF attribute without static tag' }
    ];

    patterns.forEach(pattern => {
      let match;
      while ((match = pattern.regex.exec(content)) !== null) {
        // Skip URLs and django tags
        if (match[1].startsWith('http') ||
            match[1].includes('{% url') ||
            match[1].includes('#')) {
          continue;
        }

        console.log(`Issue in ${path.relative(paths.django.templates, file)}: ${pattern.type} - ${match[0]}`);
        issuesFound = true;
      }
    });
  });

  if (!issuesFound) {
    console.log("No static asset issues found in templates!");
  }

  return src('.');  // Return something to work with gulp
}

// Helper function to get all files recursively
function getAllFiles(dir) {
  let results = [];
  const list = fs.readdirSync(dir);

  list.forEach(file => {
    file = path.join(dir, file);
    const stat = fs.statSync(file);

    if (stat && stat.isDirectory()) {
      results = results.concat(getAllFiles(file));
    } else {
      if (file.endsWith('.html')) {
        results.push(file);
      }
    }
  });

  return results;
}

// Clean .temp folder
function cleanTemp(callback) {
  del.sync(paths.temp.basetemp);
  callback();
}

// Browser Sync Serve (Development)
// function browsersyncServe(callback) {
//   browsersync.init({
//     server: {
//       baseDir: [paths.temp.basetemp, paths.src.basesrc, paths.base.base],
//     },
//     notify: false
//   });
//   callback();
// }

function browsersyncServe(callback) {
    browsersync.init({
      proxy: "http://localhost:8000",  // Proxy Django
      files: [
        paths.django.templates + "/**/*.html",  // Watch final templates
        paths.django.static + "/**/*"           // Watch static files
      ],
      notify: false,
      open: false  // Disable auto-opening browser
    });
    callback();
  }

// SyncReload
function syncReload(callback) {
  browsersync.reload();
  callback();
}

// Watch Task
// function watchTask() {
//   watch(paths.src.html, series(djangoTemplates, fixMissedStaticRefs, syncReload));
//   watch([paths.src.images, paths.src.fonts], series(images, fonts));
//   watch(
//     [paths.src.tailwind, paths.src.html, TD_CONFIG],
//     series(tcss, syncReload)
//   );
//   watch(paths.src.js, series(js, syncReload));
// }

function watchTask() {
    function touchTemplates(done) {
        const templateFiles = getAllFiles(paths.django.templates);
        const now = new Date();

        templateFiles.forEach(file => {
          fs.utimesSync(file, now, now);
        });

        done();
      }

    // Rebuild assets on change (no Browsersync reload)
    watch(paths.src.html, series(djangoTemplates, fixMissedStaticRefs, touchTemplates));
    // watch([paths.src.tailwind, TD_CONFIG], series(tcss));
    watch(paths.src.js, series(js));
    watch(paths.src.images, series(images));
    watch(paths.src.fonts, series(fonts));
  }

// Default Task Preview (Development)
exports.default = series(
  createDjangoFolders,
  parallel(css, js, images, fonts, djangoTemplates),
  fixMissedStaticRefs,
  browsersyncServe,
  watchTask
);

// Build Task for Django
exports.build = series(
  createDjangoFolders,
  cleanDjangoStatic,
  parallel(css, js, images, fonts, djangoTemplates),
  fixMissedStaticRefs,
  copyLibs
);

// export tasks
exports.css = css;
// exports.tcss = tcss;
exports.js = js;
exports.djangoTemplates = djangoTemplates;
exports.images = images;
exports.fonts = fonts;
exports.createDjangoFolders = createDjangoFolders;
exports.cleanDjangoStatic = cleanDjangoStatic;
exports.checkStaticAssets = checkStaticAssets;
exports.fixMissedStaticRefs = fixMissedStaticRefs;
