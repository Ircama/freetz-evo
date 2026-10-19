/* Keep startup calls within the MIPS 256 MiB jump region, before Go rodata. */
SECTIONS
{
  .plt : { *(.plt) }
}
INSERT BEFORE .text;
