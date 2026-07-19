// boost_locale_stubs.cpp
// Provides the missing `facet_id<converter<char>>::id` symbol so that
// boost::locale::to_lower / to_upper calls link without libboost_locale.
// libboost_locale cannot be built on uClibc (posix/numeric.o fails).
#include <boost/locale/conversion.hpp>

template<>
std::locale::id boost::locale::detail::facet_id<boost::locale::converter<char>>::id;
