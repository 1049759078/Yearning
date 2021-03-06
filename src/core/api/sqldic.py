import configparser
import logging
import json
from rest_framework.response import Response
from libs import baseview
from libs import con_database
from libs import exportdocx
from django.http import (
    HttpResponse,
    StreamingHttpResponse
)
from libs.serializers import SQLGeneratDic
from core.models import (
    SqlDictionary,
    DatabaseList
)

CUSTOM_ERROR = logging.getLogger('Yearning.core.views')


class exportdoc(baseview.SuperUserpermissions):
    '''
    导出数据字典为docx文档
    '''

    def post(self, request, args=None):
        try:
            conf = configparser.ConfigParser()
            conf.read('deploy.conf')
            ip = conf.get('mysql', 'address')
            user = conf.get('mysql', 'username')
            db = conf.get('mysql', 'db')
            password = conf.get('mysql', 'password')
        except Exception:
            CUSTOM_ERROR.error('''The configuration file information is missing!''')
            return HttpResponse(status=500)
        else:
            try:
                data = json.loads(request.data['data'])
                connection_name = request.data['connection_name']
                basename = request.data['basename']
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    c = exportdocx.ToWord(
                        Host=ip,
                        User=user,
                        Password=password,
                        Database=db,
                        Charset='utf8')
                    a = c.exportTables(Conn=connection_name, Schemal=basename, TableList=data)
                    return Response(
                        {
                            'status': 'docx文档已生成',
                            'url': '%s_%s_Dictionary_%s.docx' % (connection_name, basename, a)
                        }
                    )
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(status=500)


class adminpremisson(baseview.SuperUserpermissions):
    '''
    数据库字典相关 admin权限
    '''

    @staticmethod
    def DicGenerate(id, basename):
        '''
        字典生成
        '''
        _connection = DatabaseList.objects.filter(id=id).first()
        with con_database.SQLgo(
            ip=_connection.ip,
            user=_connection.username,
            password=_connection.password,
            db=basename,
            port=_connection.port
        ) as f:
            res = f.tablename()
            for i in res:
                EveryData = f.showtable(table_name=i)
                for c in EveryData:
                    SqlDictionary.objects.get_or_create(
                        Field=c['Field'],
                        Type=c['Type'],
                        Extra=c['Extra'],
                        BaseName=basename,
                        TableName=i,
                        TableComment=c['TableComment'],
                        Name=_connection.connection_name
                    )

    @staticmethod
    def GenerateTableData(basename=None, name=None, signal=None):
        '''
        生成表结构数据
        '''
        signal = int(signal)
        DictionaryInfo = SqlDictionary.objects.filter(
            BaseName=basename,
            Name=name
        ).values('TableName')
        DictionaryInfo.query.group_by = ['TableName']  # 不重复表名
        dic = []
        if signal == 1 or signal is None:
            for i in DictionaryInfo[:signal * 3]:
                tmp = SqlDictionary.objects.filter(
                    TableName=i['TableName'],
                    BaseName=basename
                ).all()
                serializers = SQLGeneratDic(tmp, many=True)
                dic.append(serializers.data)
        else:
            for i in DictionaryInfo[signal * 3 - 3:signal * 3]:
                tmp = SqlDictionary.objects.filter(
                    TableName=i['TableName'],
                    BaseName=basename
                ).all()
                serializers = SQLGeneratDic(tmp, many=True)
                dic.append(serializers.data)
        return dic

    def put(self, request, args: str = None):

        if args == 'Generation':  # 一次性自动扫描数据库表结构并且把信息插入sqldic表
            try:
                id = request.data['id']
                basename = json.loads(request.data['basename'])
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    for i in basename:
                        adminpremisson.DicGenerate(id, i)
                    return HttpResponse('ok')
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(status=500)

        elif args == 'deldic':
            try:
                Name = request.data['name']
                BaseName = request.data['basename']
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    for i in BaseName:
                        SqlDictionary.objects.filter(Name=Name, BaseName=i).delete()
                    return Response('字典已删除！')
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(status=500)

        elif args == 'edittableinfo':
            try:
                basename = request.data['basename']
                tablename = request.data['tablename']
                name = request.data['name']
                signal = request.data['hello']
                comment = request.data['comment']
                singleid = request.data['singleid']
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    if singleid == '0':
                        SqlDictionary.objects.filter(
                            BaseName=basename,
                            TableName=tablename
                        ).update(TableComment=comment)
                        tmp = adminpremisson.GenerateTableData(
                            basename=basename,
                            name=name,
                            signal=signal
                        )
                        return Response(tmp)
                    else:
                        SqlDictionary.objects.filter(
                            BaseName=basename,
                            TableName=tablename
                        ).update(TableComment=comment)
                        tmp = SqlDictionary.objects.filter(
                            BaseName=basename,
                            Name=name,
                            TableName=tablename
                        ).all()
                        serializers = SQLGeneratDic(tmp, many=True)
                        return Response([serializers.data])
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return Response('%s 表备注更新失败，请联系cookie' % tablename)

        elif args == 'editfelid':
            try:
                basename = request.data['basename']
                tablename = request.data['tablename']
                comment = request.data['comment']
                felid = request.data['felid']
                name = request.data['name']
                signal = request.data['hello']
                singleid = request.data['singleid']
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    if singleid == '0':
                        SqlDictionary.objects.filter(
                            BaseName=basename,
                            TableName=tablename,
                            Field=felid
                        ).update(Extra=comment)
                        tmp = adminpremisson.GenerateTableData(
                            basename=basename,
                            name=name,
                            signal=signal
                        )
                        return Response(tmp)
                    else:
                        SqlDictionary.objects.filter(
                            BaseName=basename,
                            TableName=tablename,
                            Field=felid
                        ).update(Extra=comment)
                        tmp = SqlDictionary.objects.filter(
                            BaseName=basename,
                            Name=name,
                            TableName=tablename
                        ).all()
                        serializers = SQLGeneratDic(tmp, many=True)
                        return Response([serializers.data])
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return Response('%s 表备注更新失败，请联系cookie' % felid)

        elif args == 'deltable':
            try:
                basename = request.data['basename']
                tablename = request.data['tablename']
                ConnectionName = request.data['ConnectionName']
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                SqlDictionary.objects.filter(
                    BaseName=basename,
                    TableName=tablename,
                    Name=ConnectionName
                ).delete()
                return Response('ok')


class dictionary(baseview.BaseView):
    def put(self, request, args=None):

        if args == 'info':
            try:
                basename = request.data['basename']
                name = request.data['name']
                TableInfoPage = int(request.data['hello'])
                TableList = int(request.data['tablelist'])
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    DictionaryInfo = SqlDictionary.objects.filter(
                        BaseName=basename,
                        Name=name
                        ).values('TableName')
                    DictionaryInfo.query.group_by = ['TableName']  # 不重复表名
                    all = []
                    for i in DictionaryInfo:
                        tmp = SqlDictionary.objects.filter(
                            TableName=i['TableName'],
                            BaseName=basename
                            ).all()
                        _serializers = SQLGeneratDic(tmp, many=True)
                        all.append(_serializers.data)
                    dic = []
                    for i in DictionaryInfo[TableInfoPage * 3 - 3:TableInfoPage * 3]:
                        tmp = SqlDictionary.objects.filter(
                            TableName=i['TableName'],
                            BaseName=basename
                            ).all()
                        _serializers = SQLGeneratDic(tmp, many=True)
                        dic.append(_serializers.data)
                    tablecomment = []
                    for i in DictionaryInfo[TableList * 10 - 10:TableList * 10]:
                        tmp = SqlDictionary.objects.filter(
                            TableName=i['TableName'],
                            BaseName=basename,
                            Name=name
                            ).values('TableComment')
                        tmp.query.group_by = ['TableComment']
                        tablecomment.append({'table': i, 'comment': tmp})
                    return Response({
                        'dic': dic,
                        'tablelist': tablecomment,
                        'tablepage': len(DictionaryInfo),
                        'all': all
                        })
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(status=500)

        elif args == 'tablelist':
            try:
                basename = request.data['basename']
                name = request.data['name']
                TableList = int(request.data['tablelist'])
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    DictionaryInfo = SqlDictionary.objects.filter(
                        BaseName=basename,
                        Name=name
                        ).values('TableName')
                    DictionaryInfo.query.group_by = ['TableName']  # 不重复表名
                    tablecomment = []
                    for i in DictionaryInfo[TableList * 10 - 10:TableList * 10]:
                        tmp = SqlDictionary.objects.filter(
                            TableName=i['TableName'],
                            BaseName=basename,
                            Name=name
                            ).values('TableComment')
                        tmp.query.group_by = ['TableComment']
                        tablecomment.append({'table': i, 'comment': tmp})
                    return Response(tablecomment)
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(status=500)

        elif args == 'single':
            try:
                basename = request.data['basename']
                name = request.data['name']
                tablename = request.data['tablename']
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    tmp = SqlDictionary.objects.filter(
                        BaseName=basename,
                        Name=name,
                        TableName=tablename
                        ).all()
                    _serializers = SQLGeneratDic(tmp, many=True)
                    return Response([_serializers.data])
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(status=500)

        elif args == 'datalist':
            try:
                basename = request.data['basename']
                name = request.data['name']
                signal = request.data['hello']
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    tmp = adminpremisson.GenerateTableData(
                        basename=basename,
                        name=name,
                        signal=signal
                        )
                    return Response(tmp)
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(status=500)

        elif args == 'getdiclist':
            try:
                name = request.data['name']
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
            else:
                try:
                    data = SqlDictionary.objects.filter(Name=name).values('BaseName')
                    data.query.distinct = ['BaseName']
                    return Response(data)
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(status=500)

    def get(self, request, args=None):
        try:
            data = SqlDictionary.objects.all().values('Name')
            data.query.distinct = ['Name']
            return Response(data)
        except Exception as e:
            CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
            return HttpResponse(status=500)

    def post(self, request, args=None):
        try:
            name = request.data['name']
        except KeyError as e:
            CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
            return HttpResponse(status=500)
        else:
            try:
                data = SqlDictionary.objects.filter(Name=name).all().values('BaseName')
                data.query.distinct = ['BaseName']
                return Response(data)
            except Exception as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=e)


def downloadFile(req):
    '''
    导出docx 文档下载接口
    '''
    filename = 'exportData/' + req.GET['url']

    def file_iterator(file_name, chunk_size=512):
        '''
        分块下载
        '''
        with open(file_name, 'rb') as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    response = StreamingHttpResponse(file_iterator(filename))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = f'attachment;filename="{filename}"'
    return response
