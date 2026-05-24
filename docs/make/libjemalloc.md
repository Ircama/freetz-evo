# libjemalloc 5.3.0
  - Homepage: [https://jemalloc.net/](https://jemalloc.net/)
  - Repository: [https://github.com/jemalloc/jemalloc](https://github.com/jemalloc/jemalloc)

libjemalloc is a general-purpose memory allocator focused on low fragmentation and stable performance.

## Typical consumers

- performance-sensitive daemons
- packages where allocator behavior is relevant on constrained systems

## Notes

In Freetz-EVO this package may be selected to avoid allocator-specific runtime issues in some software stacks.
