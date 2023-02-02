#pragma once

#include "private.h"

#include <yt/yt/server/lib/cypress_election/config.h>

#include <yt/yt/server/lib/misc/config.h>

#include <yt/yt/client/ypath/public.h>

#include <yt/yt/ytlib/api/native/public.h>

#include <yt/yt/core/ytree/yson_struct.h>

#include <yt/yt/library/dynamic_config/config.h>

namespace NYT::NQueryTracker {

////////////////////////////////////////////////////////////////////////////////

class TEngineConfigBase
    : public NYTree::TYsonStruct
{
public:
    TDuration QueryStateWriteBackoff;
    i64 RowCountLimit;

    REGISTER_YSON_STRUCT(TEngineConfigBase)

    static void Register(TRegistrar registrar);
};

DEFINE_REFCOUNTED_TYPE(TEngineConfigBase)

////////////////////////////////////////////////////////////////////////////////

class TYqlEngineConfig
    : public TEngineConfigBase
{
public:
    REGISTER_YSON_STRUCT(TYqlEngineConfig)

    static void Register(TRegistrar registrar);
};

DEFINE_REFCOUNTED_TYPE(TYqlEngineConfig)

////////////////////////////////////////////////////////////////////////////////

class TQueryTrackerDynamicConfig
    : public NYTree::TYsonStruct
{
public:
    TDuration ActiveQueryAcquisitionPeriod;
    TDuration ActiveQueryLeaseTimeout;
    TDuration ActiveQueryPingPeriod;
    TDuration QueryFinishBackoff;

    TEngineConfigBasePtr MockEngine;
    TEngineConfigBasePtr QlEngine;
    TYqlEngineConfigPtr YqlEngine;

    REGISTER_YSON_STRUCT(TQueryTrackerDynamicConfig)

    static void Register(TRegistrar registrar);
};

DEFINE_REFCOUNTED_TYPE(TQueryTrackerDynamicConfig)

////////////////////////////////////////////////////////////////////////////////

class TQueryTrackerServerConfig
    : public TServerConfig
{
public:
    NApi::NNative::TConnectionConfigPtr ClusterConnection;

    bool AbortOnUnrecognizedOptions;

    TString User;

    NYTree::IMapNodePtr CypressAnnotations;

    NCypressElection::TCypressElectionManagerConfigPtr ElectionManager;

    NDynamicConfig::TDynamicConfigManagerConfigPtr DynamicConfigManager;
    TString DynamicConfigPath;

    TString Root;

    bool CreateStateTablesOnStartup;

    REGISTER_YSON_STRUCT(TQueryTrackerServerConfig)

    static void Register(TRegistrar registrar);
};

DEFINE_REFCOUNTED_TYPE(TQueryTrackerServerConfig)

////////////////////////////////////////////////////////////////////////////////

class TQueryTrackerServerDynamicConfig
    : public TNativeSingletonsDynamicConfig
{
public:
    TQueryTrackerDynamicConfigPtr QueryTracker;

    REGISTER_YSON_STRUCT(TQueryTrackerServerDynamicConfig);

    static void Register(TRegistrar registrar);
};

DEFINE_REFCOUNTED_TYPE(TQueryTrackerServerDynamicConfig)

////////////////////////////////////////////////////////////////////////////////

} // namespace NYT::NQueryTracker