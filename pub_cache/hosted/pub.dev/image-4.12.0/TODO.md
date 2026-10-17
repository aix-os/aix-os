# Performance & memory TODO

Local only (excluded via .git/info/exclude). Estimates are from code reading,
not measurement. Measure first.

## 0. Benchmark harness
- [x] `benchmark/benchmark.dart`: synthetic 12MP inputs, time + peak RSS per
      benchmark in its own process. `dart compile exe` for AOT numbers.
- [x] Web benchmark runner: `dart test -p chrome [-c dart2wasm]
      benchmark/web_benchmark_test.dart` (3MP synthetic inputs).
- [~] VP8 transform biased shifts + reconstruct byte loops: VM 473→420ms,
      dart2js 1088→762ms (3MP). Predictors still take InputBuffers.
- [ ] dart2wasm: simple byte loops (grayscale, rotate, blur) run 3-4x slower
      than dart2js; not toUint8List views (tried). Likely dart2wasm codegen.
- [ ] Web: dart2js lossy WebP decode is ~9x slower per pixel than VM (1043ms
      for 3MP); wasm gaussianBlur/encode are slow too. Investigate.
- Note: untouched Uint8List pages don't count toward RSS, so over-allocation
  shows up mostly as earlier GCs, not RSS. Peak RSS is GC-timing sensitive.

### Baseline (4.10.2, AOT, Windows, 12MP, peak RSS of first run)
Encoders after the OutputBuffer fix: bmp_gray 3274→668ms / 79→26MB,
bmp_rgb 52→34MB, tga 42→37MB; others unchanged.
JPEG block release + validate early exit: decode_jpeg 261→227MB,
decode_image_jpeg min 542→520ms. Remaining peak is mostly Int32 coefficients
(4:4:4 12MP ≈ 144MB + ~560k Int32List headers) → Int16 flat storage next.
Flat Int16 coefficients: decode_jpeg 227→138MB, 565→469ms (vs 4.10.2:
261→138MB, 553→469ms). Pixel output identical on all 62 test JPEGs.
Direct color conversion (shared VM/web `_jpeg_image.dart`): decode_jpeg
469→378ms. Remaining: scan ~135ms (Huffman), IDCT+lines ~150ms.
Huffman lookahead + 32-bit bit reader: decode_jpeg 378→308ms, 138→116MB.
Total vs 4.10.2: 553→308ms (-44%), 261→116MB (-56%).
PNG row writes + typed unfilter: decode_png_rgb 772→326ms, rgba 1047→411ms,
apng 701→~495ms (inflate ~60ms; rest mostly paeth unfilter). Peak unchanged
(~81/106MB) → streaming inflate is the memory item.
Streaming inflate (decodeLazy): decode_png_rgb 326→214ms / 81→51MB, rgba
411→259ms / 106→65MB. IDAT chunks are still concatenated (1x compressed size).
PNG encode streaming (native): encode_png_rgb 82→15MB, rgba 107→17MB; time
~same (deflate ~600/1650ms is the floor; filter 245→160ms). Web still buffers
(archive Deflate can't stream). Lesson: AOT optimizes small filter functions
far better than the same loops inline in one big method (348 vs 160ms).
```
AOT, 4000x3000, 3 iterations
benchmark                 min ms  median ms   peak MB
decode_jpeg                551.0      552.7     260.8
decode_png_rgb             757.6      771.7      81.4
decode_png_rgba           1045.1     1047.1     106.5
decode_webp_lossy          871.5      896.1      55.3
decode_image_jpeg          542.1      542.9     261.1
decode_anim_gif            318.9      325.2      15.1
decode_anim_webp           501.0      507.4      43.5
decode_anim_apng           700.4      700.6      78.1
encode_jpeg               1172.9     1186.9      49.9
encode_png_rgb             814.7      820.1      81.7
encode_png_rgba           1880.0     1907.1     106.7
encode_bmp_rgb             103.5      104.3      51.8
encode_bmp_gray           3260.1     3273.7      79.0
encode_tga                 155.9      156.2      42.4
encode_tiff                 10.2       10.4      68.7
encode_gif                 831.4      834.6       6.6
resize_nearest              10.4       10.5       2.2
resize_linear               62.4       62.7       4.7
resize_cubic               809.0      815.2       4.7
resize_average             208.7      210.7       4.8
gaussian_blur_r5          5276.5     5282.2      72.4
convolution_sharpen        221.0      222.2       6.9
rotate_90                  269.3      274.0      36.9
flip_vertical              326.6      326.7       2.5
grayscale                  587.7      604.7      36.8
```

## Quick wins
- [x] `OutputBuffer` growth: geometric, trim in `getBytes()`, pre-size
      BMP/TGA/TIFF.
- [x] TGA encoder: 1/2-channel images write 3 bytes/pixel but the header says
      32bpp. `formats/tga_encoder.dart`
- [x] 8-bit BMP encode still ~0.7s at 12MP: was convert(withPalette), which
      also wrote wrong grays and modified the source (668→2.3ms).
- [x] (docs fixed; `frame:` already selects one) `decodeImage`/`decodeNamedImage` decode all animation frames (doc says
      single frame). Default to frame 0 or add `allFrames`/`maxFrames`.
      `formats/formats.dart:268`
- [x] JPEG: release `component.blocks` after building lines (peak ~10.5 → 7.5 B/px).
      `formats/jpeg/jpeg_data.dart:162-176`
- [x] JPEG `validate` scans whole entropy stream; return at first SOS after SOF.
      `formats/jpeg/jpeg_data.dart:62`
- [x] PNG interlaced: reuse Pixel in `_processPass` (allocates up to 64/px).
      `formats/png_decoder.dart:636-641`
- [x] WebP lossy: loop filter and upsampler on Uint8List + offsets, direct
      alpha writes: decode_webp_lossy 896→473ms, anim 507→357ms. Remaining
      (12MP): reconstruct ~172ms (predictors/transforms still InputBuffer,
      transformOne allocates Int32List(16) per 4x4 block), entropy ~128ms,
      filter ~104ms, upsample ~73ms.
- [x] `bakeOrientation`: rotate straight from the source, clone only for
      flips (portrait copyResize 69→39MB).
- [x] (portrait resize 63→18ms, 39→4.7MB) Fold orientation into copyResize's coordinate mapping so no rotated
      intermediate image exists at all.
- [x] JPEG encoder: `_initCategoryNumber` allocates 65k Lists per encoder; compute
      category on the fly or static typed table. Reuse Pixel in `_calculateYUV`.
      `formats/jpeg_encoder.dart:211,480-497`
- [x] flip: row swaps / pixel reversal (flipVertical 327→1.7ms).
- [x] grayscale RGB(A) uint8 fast path (605→31ms; `double.clamp` was most of it).
- [x] copyCrop/trim/direct composite: byte copies (crop 3MP 100→1.6ms).
      `transform/flip.dart:52-71`, `transform/copy_crop.dart:91`,
      `draw/composite_image.dart:118-127`
- [x] LUTs for uint8 gamma / adjustColor (no sat/hue/mask): ~50x.
      `filter/gamma.dart:20`, `filter/adjust_color.dart:115,144`
- [x] Distortion filters clone each frame (billboard, bulge, chromatic_aberration,
      hexagon_pixelate, stretch): reuse one scratch buffer.
- [x] Dithering a palette image crashed (error was diffused into indices).
- [x] (won't do: ~11ms) GIF encoder LZW (only ~11ms): read uint8 index buffer directly. `formats/gif_encoder.dart:245`

## Core: raw-byte fast paths
- [x] (done per filter/codec as byte fast paths) Shared helpers for uint8, no-palette images operating on `Uint8List` /
      `Uint32List` + rowStride instead of virtual Pixel getters + `num` math.
      Root cause for most CPU findings (`image/pixel_uint8.dart:146`).
- [x] (won't do) `getPixelCubic` allocates 16 Pixels per sample: reusing per-tap
      Pixels measured no faster (VM allocation is cheap); reverted.
- [x] (tried for the JPEG scan bit reader: no measurable gain; reverted) Typed `Uint8List` byte reader for hot decoder loops (InputBuffer.buffer is
      polymorphic `List<int>`). `util/input_buffer.dart:10`

## Decoding
- [x] JPEG Huffman: bit buffer + 9-bit lookahead table (now: 1 bit at a time,
      allocates HuffmanParent per symbol). `formats/jpeg/jpeg_scan.dart:128-160`
- [x] JPEG coefficients: flat `Int16List` per component (now Int32List(64) per
      block, ~280k objects at 12MP). `formats/jpeg/jpeg_frame.dart:40-45`
- [x] JPEG color conversion: write directly into image bytes, no per-pixel closure.
      Opt-in 1-channel output for grayscale. `formats/jpeg/_jpeg_quantize_io.dart:213-264`
- [x] JPEG scaled decode (`scale:` 2/4/8): scale 8 is DC only (310→80ms,
      116→70MB at 12MP); 2/4 average the IDCT output.
- [x] Scale 8 keeps DC only, skips progressive AC scans (70→2.3MB at 12MP).
- [ ] Scaled decode: reduced IDCTs for 2/4 (still full IDCT + average), and DC-only coefficient storage for
      baseline scale 8 (coefficients are most of the remaining memory).
- [x] Baseline JPEG decoded a band (MCU row) at a time via JpegData.decodeImage
      (12MP: 116→35MB, 310→294ms; scale 2 9MB, scale 8 0.6MB). Falls back to
      a full decode for later scans or APP1/APP14 after the scan. Note:
      Int16List.fillRange is slow on the VM; setRange from zeros is fast.
- [x] PNG: 8-bit rows without tRNS → `setRange` into image; 16-bit byte-swap.
      Split unfilter loops (no per-byte branches). `formats/png_decoder.dart:649-697`
- [x] PNG: streaming inflate (`decodeLazy`), keep 2 rows. `formats/png_decoder.dart:330,376`
- [x] WebP lossless: direct byte writes (51→45ms at 0.75MP). `formats/webp/vp8l.dart:662-673`
- [x] GIF: `setRange` lines in `_updateImage`; byte-loop compositing
      (anim 325→244ms); fixed disposal-2 fill missing the last pixel.
      `formats/gif_decoder.dart:251,348`

## Encoding
- [x] JPEG: uint8 fast path in `_calculateYUV`; 32-bit accumulator bit writer;
      (encode_jpeg 1175→498ms, 50→14MB, byte-identical)
      typed Huffman tables. `formats/jpeg_encoder.dart:194-243,850-890`
- [x] PNG: filter into 2-row buffer + chunked deflate → multiple IDAT/fdAT.
      `formats/png_encoder.dart:72-105`
- [x] PNG filters: specialize bpc==1, hoist first-row/first-pixel branches.
      Optional `PngFilter.adaptive`. `formats/png_encoder.dart:369-441`
- [x] Dither: byte fast path (zigzag/hilbert need the full copy, so no ring
      buffer); neural search on a flat map + exact result cache (gif 834→391ms).
      `filter/dither_image.dart:205,212,245`
- [x] Octree quantizer: byte loop (651→603ms at 12MP). Measured +25MB at
      12MP; the per-pixel heap update is inherent to the algorithm.
      `util/octree_quantizer.dart`
- [x] Neural quantizer: Float64List state, Int32List palette copy, Pixel reuse.
      `util/neural_quantizer.dart:101-103,146,327`
- [x] TIFF: avoid `Uint8List.fromList` copy of raw data. `formats/tiff_encoder.dart:48`
- [x] TGA/BMP 24/32: row copy + swizzle instead of per-byte writes.
- [x] (won't do: would change output sizes) Web: consider lower default deflate level.

## Processing
- [x] separableConvolution/gaussianBlur: uint8 fast path (ring of 2r+1 rows,
      padded rows, Float64 taps, bit-identical): 5282→768ms, no full temp.
      Fixed radius > image crash. Remaining: mask path still generic (mask is
      mixed on both passes); fixed-point or box-blur approximation would be
      faster but not bit-identical.
- [x] convolution/sobel (+emboss/smooth/sketch via them): row caches, no clone
      (227→17ms, 286→8ms at 0.75MP); edgeGlow too.
- [x] copyResize byte fast paths (`_resize_bytes.dart`), bit-identical to the
      per-pixel code: nearest 10.5→2.2ms, linear 63→15, cubic 815→84, average
      211→34. Fixed getPixelCubic `icp` tap (checked px instead of py).
- [x] `resize` in place: byte downscale for nearest/linear/average (linear
      176→13ms, average 291→56ms). Cubic keeps its ring-buffered path.
- [ ] copyResize: separable two-pass / precomputed weights could be faster
      still, and area weights would downscale better (not bit-identical).
- [x] copyRotate 90/180/270: byte copies via `_pixel_bytes.dart` (274→50ms).
      Tiled transpose could be faster still.
- [x] (won't do: dropping the Command frees them) Command pipeline: opt-in release of intermediate `outputImage`s.
      `command/command.dart:121`

## High-end / parallel
- [x] (won't do: Command.executeThread/getImageThread exist) `decodeImageAsync` / `encodeXAsync` via `Isolate.run` +
      `TransferableTypedData`. Replace per-call `Isolate.spawn` in
      `command/_executor_io.dart`.
- [ ] Row-band parallelism across isolates (with halo) for blur, cubic resize,
      rotate, sobel, JPEG IDCT/color. Needs the raw-byte kernel refactor first.
- [ ] GIF: quantize/dither frame N+1 while LZW-encoding frame N.
- [ ] SIMD (Int32x4) for IDCT / YCbCr, native only, behind conditional import.

## Library bugs found while adding test assertions / writing docs (not fixed)
Filters:
- [ ] pixelate average mode: block average recomputed per pixel (`y2 <= ly`) in place; partial edge blocks divided by size*size. `filter/pixelate.dart:68,84`
- [ ] stretchDistortion clamps to `w - 1` where w is already width-1 (last row/col). `filter/stretch_distortion.dart:40`
- [ ] luminanceThreshold(outputColor: true) uses `b *=`. `filter/luminance_threshold.dart:29`
- [ ] contrast ignores ContrastMode.scurve (else nested in proportional branch); throws on float, wrong on uint16; global LUT cache. `filter/contrast.dart:42`
- [ ] dropShadow: `newImageWidth = imageOffsetX` (should be +=); positive offsets never applied. `filter/drop_shadow.dart:32`
- [ ] BinaryQuantizer compares 0..255 luminance to 0.5. `util/binary_quantizer.dart:31`
- [ ] ditherImage serpentine: kernel not mirrored on reversed rows; column 0 skipped on reversed rows; generic path skips tap 0.
- [ ] gaussianBlur: kernel sums < 1 + truncation → white becomes 253 at some radii.
- [ ] adjustColor: unset whites/mids default 0 (black / divide by zero); exposure can't darken.
- [ ] bleachBypass mask ignored; copyImageChannels mask mixes raw and normalized; hexagonPixelate centerX/Y ineffective.
- [ ] histogram/hdrToLdr/reinhard/solarize/normalize: 8-bit assumptions, first frame only, alpha handling.
Draw/transform:
- [x] fillFlood threshold 0 fills partially (live seed Pixel); mutates caller's color.a. (4.12.0)
- [ ] fillRect semi-transparent color without radius sets alpha 0; rounded drawRect ignores thickness.
- [ ] drawLine antialias thickness 1 ignores mask; steep thick branch ignores blend.
- [ ] drawPixel BlendMode.direct ignores alpha/mask (drawChar fills glyph box).
- [x] drawString wrap redraws line per word. (4.12.0)
- [ ] compositeImage: larger src squashed (srcW/H not clamped); mask coords differ for direct vs other modes; center uses full src size.
- [ ] resize in place with maintainAspect + backgroundColor and equal aspect returns solid background.
- [ ] copyResizeCropSquare with radius returns first frame only.
- [ ] readFont/BitmapFont.fromFnt throws on standard `page id=0`.
Formats/image:
- [ ] TIFF tiled decode wrong in partial edge tiles (`tiff_image.dart _decodeTile`); TiffEncoder copies stale tile tags.
- [ ] PNG decoder drops APNG loopCount; APNG pHYs/tEXt rewritten per frame after IDAT; fcTL dispose byte 1 vs comment 0; encodePngFile lacks cicpData.
- [ ] encodeGif/encodeGifFile ignore `repeat`.
- [ ] GIF decoder disposal/compositing (uses current frame disposal; restore-to-previous starts blank).
- [ ] frameType never set to animation; findEncoderForNamedImage('.cur') returns IcoEncoder; CurEncoder and Rational not exported.
- [ ] EXIF GPS helpers write DOUBLE not RATIONALs; tag name lookup only uses exifImageTags; ExifData.read always false; sub-IFD getters create empty IFDs.
- [ ] PvrEncoder rgb2/rgba2 header mismatch.
- [ ] PvrEncoder PVRTC 4bpp output decodes as noise (decoder is fine: globe.pvr correct). `pvr/pvr_packet.dart`?
- [ ] Pixel.isValid excludes last row/col; convertColor added alpha defaults 0; getBytes(order:) on 4ch palette returns indices; convert(withPalette) throws for >256 colors; uint16 setters wrap; copyResize lazily creates exif on src; decodeImage on 3 bytes throws (PSD isValidFile); Image(withPalette, paletteFormat uint1/2/4) no palette.
