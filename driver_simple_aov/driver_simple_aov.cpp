#include <ai.h>
#include <string>
#include <fstream>
#include <unordered_map>

// This driver will write to a file a list of all the objects in a pointer AOV

AI_DRIVER_NODE_EXPORT_METHODS(DriverPtrMtd);
namespace ASTR {
	const AtString name("name");
	const AtString filename("filename");
};

typedef struct {
	std::unordered_map<AtString, AtNode*, AtStringHash> names;
} DriverPtrStruct;

node_parameters
{
   AiParameterStr(ASTR::filename, "objects.txt");
}

node_initialize
{
   DriverPtrStruct *driver = new DriverPtrStruct();
// initialize the driver
AiDriverInitialize(node, false);
AiNodeSetLocalData(node, driver);
}

driver_needs_bucket
{
   return true;
}

driver_process_bucket
{ }

node_update
{ }

driver_supports_pixel_type
{
	// this driver will only support pointer formats
	return pixel_type == AI_TYPE_POINTER || pixel_type == AI_TYPE_NODE;
}

driver_open
{ // this driver is unusual and happens to do all the writing at the end, so this function is
  // empty.
}

driver_extension
{
   static const char *extensions[] = { "txt", NULL };
   return extensions;
}

driver_prepare_bucket
{ }

driver_write_bucket
{
   DriverPtrStruct *driver = (DriverPtrStruct *)AiNodeGetLocalData(node);
   const void *bucket_data;
   // Iterate over all the AOVs hooked up to this driver
   while (AiOutputIteratorGetNext(iterator, NULL, NULL, &bucket_data))
   {
	  for (int y = 0; y < bucket_size_y; y++)
	  {
		 for (int x = 0; x < bucket_size_x; x++)
		 {
			 // Get source bucket coordinates for pixel
			 int sidx = y * bucket_size_x + x;
			 // Because of driver_supports_pixel_type, we know pixel is a
			 // pointer to an AtNode.
			 AtNode* pixel_node = ((AtNode **)bucket_data)[sidx];
			 const AtString name = AiNodeGetStr(pixel_node, ASTR::name);
			 driver->names.emplace(name, pixel_node);
		  }
	   }
	}
}

driver_close
{
   DriverPtrStruct *driver = (DriverPtrStruct *)AiNodeGetLocalData(node);
   std::ofstream myfile(AiNodeGetStr(node, ASTR::filename));
   for (auto &i : driver->names)
	  myfile << i.first << ":\t " << i.second << std::endl;
   myfile.close();
}

node_finish
{
	// Free local data
	DriverPtrStruct *driver = (DriverPtrStruct *)AiNodeGetLocalData(node);
	delete driver;
}

node_loader
{
   if (i > 0)
	  return false;
   node->methods = (AtNodeMethods*)DriverPtrMtd;
   node->output_type = AI_TYPE_NONE;
   node->name = "driver_ptr";
   node->node_type = AI_NODE_DRIVER;
   strcpy(node->version, AI_VERSION);
   return true;
}