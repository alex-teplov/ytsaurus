#include "common.h"

#include <yt/yt/client/ypath/rich.h>

#include <yt/yt/core/ytree/fluent.h>

#include <util/string/split.h>

namespace NYT::NQueueClient {

using namespace NYson;
using namespace NYTree;
using namespace NYPath;

////////////////////////////////////////////////////////////////////////////////

bool TCrossClusterReference::operator==(const TCrossClusterReference& other) const
{
    return Cluster == other.Cluster && Path == other.Path;
}

bool TCrossClusterReference::operator<(const TCrossClusterReference& other) const
{
    return std::tie(Cluster, Path) < std::tie(other.Cluster, other.Path);
}

TCrossClusterReference::operator TRichYPath() const
{
    TRichYPath result = Path;
    result.SetCluster(Cluster);
    return result;
}

TCrossClusterReference TCrossClusterReference::FromString(TStringBuf path)
{
    TCrossClusterReference result;
    if (!StringSplitter(path).Split(':').Limit(2).TryCollectInto(&result.Cluster, &result.Path)) {
        THROW_ERROR_EXCEPTION("Ill-formed cross-cluster reference %Qv", path);
    }
    if (result.Cluster.empty()) {
        THROW_ERROR_EXCEPTION("The cluster component of cross-cluster reference %Qv cannot be empty", path);
    }
    if (result.Path.empty()) {
        THROW_ERROR_EXCEPTION("The path component of cross-cluster reference %Qv cannot be empty", path);
    }
    return result;
}

TString ToString(const TCrossClusterReference& queueRef)
{
    return Format("%v:%v", queueRef.Cluster, queueRef.Path);
}

void Serialize(const TCrossClusterReference& queueRef, IYsonConsumer* consumer)
{
    BuildYsonFluently(consumer).Value(ToString(queueRef));
}

////////////////////////////////////////////////////////////////////////////////

} // namespace NYT::NQueueClient

size_t THash<NYT::NQueueClient::TCrossClusterReference>::operator()(const NYT::NQueueClient::TCrossClusterReference& crossClusterRef) const
{
    using NYT::HashCombine;

    size_t result = 0;
    HashCombine(result, crossClusterRef.Cluster);
    HashCombine(result, crossClusterRef.Path);
    return result;
}
