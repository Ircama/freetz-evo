#include "MatterEnvironmentGroups.h"
#include <cassert>

int main()
{
    const std::map<int, std::vector<int>> topology = {
        {0, {1, 2, 3, 4, 5, 6, 7, 8}}, {1, {2, 6}},
        {2, {3, 4, 5}}, {3, {}}, {4, {}}, {5, {}},
        {6, {7, 8}}, {7, {}}, {8, {}}
    };
    const auto bridged = matter_environment::groups(topology, {1});
    assert(bridged.at(2) == 2);
    assert(bridged.at(3) == 2);
    assert(bridged.at(4) == 2);
    assert(bridged.at(5) == 2);
    assert(bridged.at(6) == 6);
    assert(bridged.at(7) == 6);
    assert(bridged.at(8) == 6);
    const auto legacy = matter_environment::groups(topology, {});
    for (const auto& endpoint : legacy)
        assert(endpoint.second == 0);
    const auto nested = matter_environment::groups({{0, {1, 2, 3, 4}}, {1, {2, 3, 4}}, {2, {3, 4}}, {3, {4}}, {4, {}}}, {1});
    assert(nested.at(4) == 2);
    const auto cycle = matter_environment::groups({{1, {2, 3}}, {2, {3}}, {3, {2}}}, {1});
    assert(cycle.at(2) == 2);
    assert(cycle.at(3) == 3);
}