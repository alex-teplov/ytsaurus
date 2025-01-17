#pragma once

#include "public.h"

#include <yt/yt/server/master/object_server/object.h>

#include <yt/yt/server/master/security_server/public.h>

#include <yt/yt/client/table_client/schema.h>

#include <library/cpp/yt/small_containers/compact_flat_map.h>

#include <library/cpp/yt/threading/rw_spin_lock.h>

namespace NYT::NTableServer {

///////////////////////////////////////////////////////////////////////////////

class TMasterTableSchema
    : public NObjectServer::TObject
{
public:
    using TTableSchemaToObjectMap = THashMap<
        NTableClient::TTableSchemaPtr,
        TMasterTableSchema*,
        NTableClient::TTableSchemaHash,
        NTableClient::TTableSchemaEquals
    >;
    using TTableSchemaToObjectMapIterator = TTableSchemaToObjectMap::iterator;

    using TAccountToMasterMemoryUsage = TCompactFlatMap<NSecurityServer::TAccount*, i64, 2>;
    using TAccountToRefCounterMap = TCompactFlatMap<NSecurityServer::TAccount*, i64, 2>;

    // These are transient and are used for master memory accounting only.
    DEFINE_BYREF_RO_PROPERTY(TAccountToMasterMemoryUsage, ChargedMasterMemoryUsage);
    DEFINE_BYREF_RO_PROPERTY(TAccountToRefCounterMap, ReferencingAccounts);

    using TObject::TObject;
    TMasterTableSchema(TMasterTableSchemaId id, TTableSchemaToObjectMapIterator it);

    void Save(NCellMaster::TSaveContext& context) const;
    void Load(NCellMaster::TLoadContext& context);

    const NTableClient::TTableSchemaPtr& AsTableSchema() const;
    const TFuture<NYson::TYsonString>& AsYsonAsync() const;
    // Whenever possible, prefer the above.
    NYson::TYsonString AsYsonSync() const;

    //! Increases the number of times this schema is referenced by #account.
    //! Returns true iff this schema has just become referenced by it for the
    //! first time (i.e. iff refcounter has become equal to one).
    [[nodiscard]] bool RefBy(NSecurityServer::TAccount* account);
    //! Decreases the number of times this schema is referenced by #account.
    //! Returns true iff this schema is no longer referenced by it (i.e. iff
    //! refcounter has come down to zero).
    [[nodiscard]] bool UnrefBy(NSecurityServer::TAccount* account);

    i64 GetMasterMemoryUsage(NSecurityServer::TAccount* account) const;
    i64 GetChargedMasterMemoryUsage(NSecurityServer::TAccount* account) const;
    void SetChargedMasterMemoryUsage(NSecurityServer::TAccount* account, i64 usage);

private:
    friend class TTableManager;

    using TBase = NObjectServer::TObject;

    TTableSchemaToObjectMapIterator TableSchemaToObjectMapIterator_;
    NTableClient::TTableSchemaPtr TableSchema_;

    mutable TFuture<NYson::TYsonString> MemoizedYson_;
    YT_DECLARE_SPIN_LOCK(NThreading::TReaderWriterSpinLock, MemoizedYsonLock_);

    TTableSchemaToObjectMapIterator GetTableSchemaToObjectMapIterator() const;
    void SetTableSchemaToObjectMapIterator(TTableSchemaToObjectMapIterator it);
    void ResetTableSchemaToObjectMapIterator();
};

////////////////////////////////////////////////////////////////////////////////

} // namespace NYT::NTableServer
