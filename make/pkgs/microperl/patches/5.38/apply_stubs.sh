#!/bin/sh
# Apply stub implementations required for microperl 5.38 build.
# Called from PATCH_POST_CMDS in microperl.mk - executed from the
# unpacked source directory. Using here-documents avoids all quoting
# issues that arise when echo -e strings are embedded in Makefile
# PATCH_POST_CMDS variables (which are wrapped in sh -c '...' or
# sh -c "..." by the framework).

# Append C stub functions to op.c
cat >> op.c << 'STUBS_EOF'

/*
 * Stub implementations for functions not available in PERL_MICRO
 */

void
Perl_optimize_optree(pTHX_ OP *o)
{
    /* No-op in microperl */
}

void
Perl_finalize_optree(pTHX_ OP *o)
{
    /* No-op in microperl */
}

void
Perl_peep(pTHX_ OP *o)
{
    /* No-op in microperl */
}

void
Perl_rpeep(pTHX_ OP *o)
{
    /* No-op in microperl */
}
STUBS_EOF

# Append Perl stubs to lib/warnings.pm
cat >> lib/warnings.pm << 'WARNINGS_EOF'

sub register_categories {
    # Stub for microperl
}

sub enabled {
    # Stub for microperl - always return 0
    return 0;
}
sub warn {
    # Stub for microperl
}
sub warnif {
    # Stub for microperl
}
WARNINGS_EOF

# Append Perl stub to lib/Encode.pm
cat >> lib/Encode.pm << 'ENCODE_EOF'

sub onBOOT {
    # Stub for microperl
}
ENCODE_EOF
