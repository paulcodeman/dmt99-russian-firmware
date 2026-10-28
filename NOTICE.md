# Attribution and distribution

This independent project is not affiliated with or endorsed by FNIRSI.

- The original DMT-99 V2.4 application is downloaded from [FNIRSI](https://www.fnirsi.com/pages/manuals-firmwares) and accepted only when its SHA-256 is `4befdf6b58e063f03901f190000d790e60d20d0a23e5eeb2b6f6840f1830e98e`. Manufacturer firmware remains the property of its rights holders.
- Address mappings, stock behavior research and offline instruction semantics were studied using [smhgzll/dmt-99-multimeter-custom-firmware](https://github.com/smhgzll/dmt-99-multimeter-custom-firmware), pinned to commit `1fef86f4a6d7417cd47ae4ef1f60d302e0dfc737`. Its interpreter and fixtures are fetched for verification into an ignored cache, with individual hashes in `inputs.lock.json`; this repository does not relicense or redistribute them.
- The included font bitmaps were generated from DejaVu Sans Mono Bold. The Bitstream/DejaVu notice is preserved in `src/DejaVu-LICENSE.txt`.
- Pillow and the GNU RISC-V toolchain are separate development dependencies.

Public releases contain an IPS patch, our compiled overlay, source references,
verification results and a tool that downloads and verifies the manufacturer
image to create a BIN locally. The original manufacturer BIN, resource dump,
and combined firmware image are excluded from public release assets and Git.

The patch is experimental. Software UI tests do not establish physical startup,
bootloader recovery, measurement accuracy, electrical safety ratings or timing
on a real device. A stock BIN can only be restored when the bootloader remains
accessible. Hardware validation is currently **not confirmed**.
